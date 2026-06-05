import os
import json
import logging
import asyncio
import time
import re
import uuid
import hashlib
from typing import List, Literal, Optional
from dotenv import load_dotenv
import sentry_sdk
from supabase import create_client, Client
from groq import Groq
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
from json_repair import repair_json

from agents.observability import init_observability, load_pipeline_state, update_pipeline_run_metric

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize observability
init_observability()

# Load env
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in env")

if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY is missing! The agent will fail if Groq API calls are attempted.")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is missing! The agent will fail if Gemini API calls are attempted.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Read version-controlled prompts — version driven by config/prompt_versions.yaml
def _load_prompt_version_config() -> dict:
    """Load active prompt versions from config/prompt_versions.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompt_versions.yaml")
    defaults = {"classify_prompt": "classify_v1", "extract_prompt": "extract_v2", "digest_prompt": "digest_v1"}
    if not os.path.exists(config_path):
        return defaults
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {**defaults, **{k: v for k, v in data.items() if v}}
    except Exception as e:
        logger.warning(f"Could not load prompt_versions.yaml, using defaults: {e}")
        return defaults

_prompt_versions = _load_prompt_version_config()

# Allow env-var override for CI/test scenarios
ACTIVE_CLASSIFY_VERSION = os.getenv("CLASSIFY_PROMPT_VERSION") or _prompt_versions.get("classify_prompt", "classify_v1")
ACTIVE_EXTRACT_VERSION = os.getenv("EXTRACT_PROMPT_VERSION") or _prompt_versions.get("extract_prompt", "extract_v2")

CLASSIFY_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{ACTIVE_CLASSIFY_VERSION}.txt")
try:
    with open(CLASSIFY_PROMPT_PATH, "r", encoding="utf-8") as f:
        CLASSIFY_SYSTEM_PROMPT = f.read()
    logger.info(f"Loaded classify prompt: {ACTIVE_CLASSIFY_VERSION}")
except FileNotFoundError:
    logger.error(f"Classify prompt file not found at {CLASSIFY_PROMPT_PATH}")
    CLASSIFY_SYSTEM_PROMPT = "You are an AI research analyst. Respond ONLY with valid JSON."

EXTRACT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{ACTIVE_EXTRACT_VERSION}.txt")
try:
    with open(EXTRACT_PROMPT_PATH, "r", encoding="utf-8") as f:
        EXTRACT_SYSTEM_PROMPT = f.read()
    logger.info(f"Loaded extract prompt: {ACTIVE_EXTRACT_VERSION}")
except FileNotFoundError:
    logger.error(f"Extract prompt file not found at {EXTRACT_PROMPT_PATH}")
    EXTRACT_SYSTEM_PROMPT = "You are an expert AI research analyst. Deeply analyze the document and return structured JSON."


# --- Pydantic Validation Models ---
class ClassificationResult(BaseModel):
    category: Literal['paper', 'tool', 'product', 'company', 'newsletter', 'event', 'other']
    subcategory: str
    importance: int = Field(ge=0, le=100)
    is_ai_relevant: bool
    technical_depth: Literal['low', 'medium', 'high']
    entities_mentioned: List[str]
    reason: str


class InsightResult(BaseModel):
    headline: str = Field(max_length=50)
    tldr: List[str] = Field(min_length=3, max_length=3)
    technical_depth: str
    practical_utility: str
    ecosystem_impact: str
    related_entities: List[str]
    tags: List[str]
    category: Literal['paper', 'tool', 'product', 'company', 'newsletter', 'event', 'other']
    source_url: Optional[str] = None
    published_at: Optional[str] = None
    related_papers: Optional[List[str]] = []
    source_reliability_note: Optional[str] = ""


class TokenBucketLimiter:
    def __init__(self, rate_limit: float = 0.25, capacity: float = 5.0):
        self.rate_limit = rate_limit
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def wait_for_token(self):
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_limit)
                self.last_refill = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                sleep_dur = (1.0 - self.tokens) / self.rate_limit
                await asyncio.sleep(sleep_dur)


def extract_arxiv_sections(text: str) -> str:
    if not text:
        return ""
    abstract = ""
    intro = ""
    conclusion = ""
    
    abstract_match = re.search(r'\babstract\b', text, re.IGNORECASE)
    intro_match = re.search(r'\b(1\.?\s+)?introduction\b', text, re.IGNORECASE)
    
    if abstract_match and intro_match and intro_match.start() > abstract_match.end():
        abstract = text[abstract_match.start():intro_match.start()].strip()
    elif intro_match:
        abstract = text[:intro_match.start()].strip()
    else:
        abstract = text[:5000].strip()

    if intro_match:
        intro_start = intro_match.start()
        next_heading_patterns = [
            r'\n\s*(2|ii)\.?\s+[a-z]',
            r'\n\s*related\s+work',
            r'\n\s*background',
            r'\n\s*methods?',
            r'\n\s*system\s+design'
        ]
        next_heading_pos = len(text)
        for pattern in next_heading_patterns:
            match = re.search(pattern, text[intro_start:], re.IGNORECASE)
            if match:
                pos = intro_start + match.start()
                if pos < next_heading_pos:
                    next_heading_pos = pos
        intro = text[intro_start:next_heading_pos].strip()

    conclusion_match = re.search(r'\b(conclusion|conclusions)\b', text, re.IGNORECASE)
    if conclusion_match:
        conclusion_start = conclusion_match.start()
        ref_match = re.search(r'\b(references|bibliography|acknowledgements?)\b', text[conclusion_start:], re.IGNORECASE)
        if ref_match:
            conclusion = text[conclusion_start : conclusion_start + ref_match.start()].strip()
        else:
            conclusion = text[conclusion_start:].strip()

    combined = []
    if abstract:
        combined.append(f"--- ABSTRACT ---\n{abstract}")
    if intro:
        combined.append(f"--- INTRODUCTION ---\n{intro}")
    if conclusion:
        combined.append(f"--- CONCLUSION ---\n{conclusion}")
        
    result = "\n\n".join(combined).strip()
    if len(result) < 100:
        return text[:100000]
    return result[:100000]


def build_classify_user_prompt(title: str, text: str) -> str:
    return f"""Classify this article for an AI intelligence feed.
Article title: {title}
Article text: {text[:800]}"""


# Global execution metrics tracking
run_stats = {
    "run_id": None,
    "total_groq_attempts": 0,
    "failed_groq_validations": 0,
    "total_gemini_attempts": 0,
    "failed_gemini_validations": 0,
    # Prompt version tracking — written to pipeline_runs at end of run
    "prompt_version": ACTIVE_CLASSIFY_VERSION,
    # Classification accuracy — set externally by eval_classify_prompt.py or left None
    "classification_accuracy": None,
}


def validate_and_repair_json(raw_text: str, pydantic_model) -> tuple[Optional[BaseModel], bool, Optional[str]]:
    try:
        data = json.loads(raw_text)
        return pydantic_model(**data), False, None
    except Exception as e:
        first_err = str(e)

    try:
        repaired = repair_json(raw_text)
        data_repaired = json.loads(repaired)
        return pydantic_model(**data_repaired), True, None
    except Exception as e:
        second_err = str(e)

    return None, False, f"Original error: {first_err} | Repair error: {second_err}"


def record_failed_extraction(doc_id: str, model_name: str, raw_output: str, error_msg: str, run_id: uuid.UUID):
    logger.error(f"Validation failed for doc {doc_id} under model {model_name}. Logging failure.")
    try:
        supabase.table("failed_extractions").insert({
            "doc_id": doc_id,
            "model": model_name,
            "raw_output": raw_output,
            "error": error_msg,
            "run_id": str(run_id)
        }).execute()
    except Exception as e:
        logger.error(f"Failed to write to failed_extractions: {e}")


def run_groq_classification() -> int:
    logger.info("Phase 4.1: Groq Classification starting...")
    if not groq_client:
        logger.error("Groq client not initialized, skipping classification.")
        return 0
        
    successful_count = 0
    try:
        res = supabase.table("articles")\
            .select("id, title, clean_text, url, raw_html, published_at, source_id")\
            .eq("status", "deduplicated")\
            .limit(50)\
            .execute()
            
        articles = res.data or []
        if not articles:
            logger.info("No deduplicated articles found for classification.")
            return 0
            
        logger.info(f"Found {len(articles)} articles for Groq classification.")
        
        for article in articles:
            article_id = article["id"]
            title = article.get("title") or ""
            text = article.get("clean_text") or ""
            
            user_msg = build_classify_user_prompt(title, text)
            
            from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
            groq_breaker = PersistentCircuitBreaker("groq")
            gemini_breaker = PersistentCircuitBreaker("gemini")
            
            raw_response = None
            used_fallback = False
            
            def call_groq():
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.0,
                    max_tokens=300,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content

            async def call_gemini_fallback():
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=CLASSIFY_SYSTEM_PROMPT
                )
                response = await model.generate_content_async(
                    contents=user_msg,
                    generation_config={"response_mime_type": "application/json"}
                )
                return response.text

            try:
                run_stats["total_groq_attempts"] += 1
                raw_response = groq_breaker.call(call_groq)
            except (CircuitBreakerOpenException, Exception) as groq_err:
                logger.warning(f"Groq classification failed/bypassed: {groq_err}. Falling back to Gemini.")
                used_fallback = True
                try:
                    run_stats["total_gemini_attempts"] += 1
                    raw_response = asyncio.run(gemini_breaker.call_async(call_gemini_fallback))
                except Exception as gemini_err:
                    logger.error(f"Gemini fallback classification also failed: {gemini_err}")
                    run_stats["failed_gemini_validations"] += 1
                    continue

            try:
                validated_res, was_repaired, error_msg = validate_and_repair_json(raw_response, ClassificationResult)
                
                if not validated_res:
                    if used_fallback:
                        run_stats["failed_gemini_validations"] += 1
                        model_name = "gemini-2.0-flash"
                    else:
                        run_stats["failed_groq_validations"] += 1
                        model_name = "llama-3.3-70b-versatile"
                        
                    logger.warning(f"LangSmith / Observability log: classification failed for {article_id}. raw={raw_response}")
                    record_failed_extraction(
                        doc_id=article_id,
                        model_name=model_name,
                        raw_output=raw_response,
                        error=error_msg,
                        run_id=run_stats["run_id"]
                    )
                    continue
                
                importance = validated_res.importance
                is_ai_relevant = validated_res.is_ai_relevant
                status = "filtered" if (importance < 40 or not is_ai_relevant) else "escalated"
                
                clean_text = text or title or ""
                text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
                
                logger.info(f"Article {article_id} classified as {status} (importance={importance}). Upserting transactionally...")
                
                supabase.rpc("upsert_full_article_pipeline_data", {
                    "p_article_url": article.get("url"),
                    "p_article_title": article.get("title"),
                    "p_article_raw_html": article.get("raw_html"),
                    "p_article_clean_text": article.get("clean_text"),
                    "p_article_published_at": article.get("published_at"),
                    "p_article_status": status,
                    "p_article_text_hash": text_hash,
                    "p_source_id": article.get("source_id"),
                    
                    "p_class_category": validated_res.category,
                    "p_class_subcategory": validated_res.subcategory,
                    "p_class_importance": validated_res.importance,
                    "p_class_is_ai_relevant": validated_res.is_ai_relevant,
                    "p_class_technical_depth": validated_res.technical_depth,
                    "p_class_reason": validated_res.reason
                }).execute()
                successful_count += 1
                
            except Exception as api_err:
                logger.error(f"Post-processing error for article {article_id}: {api_err}")
                continue
            
        return successful_count
    except Exception as e:
        logger.error(f"Groq phase failed: {e}")
        sentry_sdk.capture_exception(e)
        raise e


# 15 RPM = 0.25 tokens/sec. Capacity is set to 10 to handle concurrent batching bursts.
gemini_limiter = TokenBucketLimiter(rate_limit=0.25, capacity=10.0)

async def extract_insight_with_gemini(article: dict, model: genai.GenerativeModel) -> bool:
    article_id = article["id"]
    title = article.get("title") or ""
    text = article.get("clean_text") or ""
    source_category = article.get("source_category") or ""
    
    if source_category == "arxiv" or "arxiv.org" in article.get("url", ""):
        prepared_text = extract_arxiv_sections(text)
    else:
        prepared_text = text[:100000]
        
    user_prompt = f"Analyze the following document:\nTitle: {title}\nContent:\n{prepared_text}"
    
    from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
    gemini_breaker = PersistentCircuitBreaker("gemini")
    
    async def call_gemini():
        response = await model.generate_content_async(
            contents=user_prompt,
            generation_config={
                "response_mime_type": "application/json",
            }
        )
        return response.text

    await gemini_limiter.wait_for_token()
    run_stats["total_gemini_attempts"] += 1
    
    try:
        raw_response = await gemini_breaker.call_async(call_gemini)
        validated_res, was_repaired, error_msg = validate_and_repair_json(raw_response, InsightResult)
        
        if not validated_res:
            run_stats["failed_gemini_validations"] += 1
            logger.warning(f"LangSmith / Observability log: extraction failed for {article_id}. raw={raw_response}")
            record_failed_extraction(
                doc_id=article_id,
                model_name="gemini-2.0-flash",
                raw_output=raw_response,
                error=error_msg,
                run_id=run_stats["run_id"]
            )
            return False
            
        clean_text = text or title or ""
        text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        tldr_bullets = validated_res.tldr or []
        
        logger.info(f"Article {article_id} deep-extraction completed. Upserting transactionally...")
        
        supabase.rpc("upsert_full_article_pipeline_data", {
            "p_article_url": article.get("url"),
            "p_article_title": article.get("title"),
            "p_article_raw_html": article.get("raw_html"),
            "p_article_clean_text": text,
            "p_article_published_at": article.get("published_at"),
            "p_article_status": "analyzed",
            "p_article_text_hash": text_hash,
            "p_source_id": article.get("source_id"),
            
            "p_insight_headline": validated_res.headline,
            "p_insight_tldr": tldr_bullets,
            "p_insight_technical_depth": validated_res.technical_depth,
            "p_insight_practical_utility": validated_res.practical_utility,
            "p_insight_ecosystem_impact": validated_res.ecosystem_impact,
            "p_insight_related_papers": validated_res.related_papers or [],
            "p_insight_related_entities": validated_res.related_entities or [],
            "p_insight_tags": validated_res.tags or [],
            "p_insight_source_reliability_note": validated_res.source_reliability_note
        }).execute()
        
        return True
        
    except CircuitBreakerOpenException:
        logger.warning(f"Gemini circuit breaker is OPEN. Skipping deep analysis for article {article_id}.")
        return False
    except Exception as e:
        logger.error(f"Gemini processing failed for article {article_id}: {e}")
        sentry_sdk.capture_exception(e)
        return False


async def run_gemini_extraction_async():
    logger.info("Phase 4.2: Gemini Deep-Extraction starting...")
    if not GEMINI_API_KEY:
        logger.error("Gemini API key not configured, skipping extraction.")
        return 0
        
    from agents.circuit_breaker import PersistentCircuitBreaker
    gemini_breaker = PersistentCircuitBreaker("gemini")
    try:
        cb_state = gemini_breaker.fetch_state()
        if cb_state and cb_state.get("state") == "open":
            logger.warning("Gemini circuit breaker is OPEN. Skipping deep analysis entirely.")
            return 0
    except Exception:
        pass

    try:
        res = supabase.table("articles")\
            .select("id, title, clean_text, url, raw_html, published_at, source_id, sources(category)")\
            .eq("status", "escalated")\
            .limit(50)\
            .execute()
            
        articles_raw = res.data or []
        if not articles_raw:
            logger.info("No escalated articles found for Gemini extraction.")
            return 0
            
        articles = []
        for a in articles_raw:
            src = a.get("sources") or {}
            source_category = src.get("category") if isinstance(src, dict) else ""
            articles.append({
                "id": a["id"],
                "title": a.get("title"),
                "clean_text": a.get("clean_text"),
                "raw_html": a.get("raw_html"),
                "published_at": a.get("published_at"),
                "source_id": a.get("source_id"),
                "url": a.get("url"),
                "source_category": source_category
            })
            
        logger.info(f"Found {len(articles)} articles to process with Gemini.")
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=EXTRACT_SYSTEM_PROMPT
        )
        new_signals_count = 0
        chunk_size = 10
        for i in range(0, len(articles), chunk_size):
            batch = articles[i:i+chunk_size]
            tasks = [extract_insight_with_gemini(article, model) for article in batch]
            batch_results = await asyncio.gather(*tasks)
            new_signals_count += sum(1 for success in batch_results if success)
            
        return new_signals_count
            
    except Exception as e:
        logger.error(f"Gemini extraction phase failed: {e}")
        sentry_sdk.capture_exception(e)
        raise e


def run_llm_analysis():
    from agents.circuit_breaker import is_supabase_open
    if is_supabase_open():
        logger.error("Supabase circuit breaker is OPEN. Bypassing LLM analysis entirely.")
        return

    # Load shared run_id from state if available
    state = load_pipeline_state()
    run_id_str = state.get("run_id") if state else None
    run_id = uuid.UUID(run_id_str) if run_id_str else uuid.uuid4()
    
    run_stats["run_id"] = run_id
    run_stats["total_groq_attempts"] = 0
    run_stats["failed_groq_validations"] = 0
    run_stats["total_gemini_attempts"] = 0
    run_stats["failed_gemini_validations"] = 0
    
    logger.info(f"Starting LLM analysis engine run. run_id={run_id}")
    
    # Run Groq classification
    successful_groq_classifications = run_groq_classification()
    
    # Run Gemini extraction asynchronously
    successful_gemini_extractions = 0
    if GEMINI_API_KEY:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop:
            raise RuntimeError("Event loop already running, cannot execute run_llm_analysis sync.")
        else:
            successful_gemini_extractions = asyncio.run(run_gemini_extraction_async())
        
    total_calls = run_stats["total_groq_attempts"] + run_stats["total_gemini_attempts"]
    total_failures = run_stats["failed_groq_validations"] + run_stats["failed_gemini_validations"]
    
    update_pipeline_run_metric(
        analyzed=successful_groq_classifications,
        new_signals=successful_gemini_extractions,
        total_llm_attempts=total_calls,
        failed_llm_validations=total_failures,
        # Persist prompt version and accuracy so delivery_agent can write them to pipeline_runs
        prompt_version=run_stats["prompt_version"],
        classification_accuracy=run_stats["classification_accuracy"],
    )
    
    if total_calls > 0:
        failure_rate = total_failures / total_calls
        logger.info(f"Run {run_id} completed. Total attempts: {total_calls}, Failures: {total_failures} ({failure_rate:.1%})")
        if failure_rate > 0.05:
            alert_msg = f"LLM validation failure rate of {failure_rate:.1%} ({total_failures}/{total_calls}) exceeded 5% limit in run {run_id}."
            logger.error(f"[ALERT] {alert_msg}")
            sentry_sdk.capture_message(alert_msg, level="error")
    else:
        logger.info("No articles processed during this run.")


if __name__ == "__main__":
    run_llm_analysis()
