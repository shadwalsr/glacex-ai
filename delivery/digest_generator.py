import os
import json
import logging
import httpx
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from pydantic import BaseModel
from typing import List, Optional

from llm.retriever import get_ensemble_retriever
from supabase import create_client, Client

logger = logging.getLogger(__name__)

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "glacex_ai_pipeline")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Read version-controlled prompt
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "digest_v1.txt")
try:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        DIGEST_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.error(f"Digest prompt file not found at {PROMPT_PATH}")
    DIGEST_SYSTEM_PROMPT = "You are an AI research editor. Compile a Daily Digest in JSON."


class DigestResult(BaseModel):
    research_breakthroughs: List[str]
    new_tools: List[str]
    product_launches: List[str]
    company_news: List[str]
    must_read_papers: List[str]


def compile_markdown_digest(digest: DigestResult) -> str:
    """Formats the structured JSON digest into a beautiful readable Markdown text."""
    lines = ["# GlaceX Daily Digest ⚡\n"]
    
    sections = [
        ("🔬 Research Breakthroughs", digest.research_breakthroughs),
        ("🛠️ New Tools", digest.new_tools),
        ("🚀 Product Launches", digest.product_launches),
        ("🏢 Company News", digest.company_news),
        ("📄 Must-Read Papers", digest.must_read_papers)
    ]
    
    for title, items in sections:
        lines.append(f"## {title}")
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("_No new updates in this category today._")
        lines.append("")
        
    return "\n".join(lines).strip()


def send_to_ntfy(message_text: str, title: str = "GlaceX Daily Digest") -> bool:
    """Sends the formatted digest to ntfy.sh."""
    if not NTFY_TOPIC:
        logger.error("NTFY_TOPIC is not configured, skipping push delivery.")
        return False

    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Priority": "default",
        "Tags": "zap,robot"
    }
    
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    try:
        response = httpx.post(url, headers=headers, content=message_text, timeout=30)
        if response.status_code == 200:
            logger.info("Successfully pushed daily digest to ntfy.sh.")
            return True
        else:
            logger.error(f"Failed to deliver to ntfy.sh: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error during ntfy delivery: {e}")
        return False


def generate_daily_digest(supabase_client: Client) -> Optional[DigestResult]:
    """Retrieves top 20 new articles, synthesizes the digest via Gemini, and returns it."""
    logger.info("Starting Daily Digest generation...")
    
    # 1. Query retriever for top 20 documents related to recent AI topics
    retriever = get_ensemble_retriever(supabase_client, match_count=20)
    query_str = "latest AI model releases, tools, frameworks, breakthroughs, research papers, company funding, startup launches"
    
    try:
        docs = retriever.invoke(query_str)
    except Exception as e:
        logger.error(f"Retriever query failed: {e}")
        return None
        
    logger.info(f"Retrieved {len(docs)} document contexts for digest synthesis.")
    
    # Compile text context
    context_list = []
    for doc in docs:
        title = doc.metadata.get("title", "Untitled")
        url = doc.metadata.get("url", "")
        content = doc.page_content[:1500] # slice each context slightly to stay safe
        context_list.append(f"Source Title: {title}\nURL: {url}\nContent:\n{content}\n---")
        
    context_text = "\n\n".join(context_list)
    
    # 2. Invoke Gemini Flash (using standard system_instruction)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=DIGEST_SYSTEM_PROMPT
    )
    
    try:
        response = model.generate_content(
            contents=f"Synthesize the daily digest from these new developments:\n\n{context_text}",
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        
        digest_json = json.loads(response.text)
        
        # 3. Validate output against Pydantic schema
        validated_digest = DigestResult(**digest_json)
        return validated_digest
        
    except Exception as e:
        logger.error(f"Gemini digest generation or validation failed: {e}")
        return None


def run_delivery_pipeline():
    """Main execution trigger for daily digest creation and push delivery."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase config missing, cannot run delivery pipeline.")
        return

    supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # Check if this is the daily run (e.g. 18:00 UTC or manual test execution)
    # For now, we will execute it whenever the script runs directly
    digest = generate_daily_digest(supabase_client)
    if digest:
        markdown_text = compile_markdown_digest(digest)
        send_to_ntfy(markdown_text)
    else:
        logger.error("Failed to generate daily digest.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_delivery_pipeline()
