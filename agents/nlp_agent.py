import os
import logging
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
import sentry_sdk
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import spacy

from agents.observability import init_observability

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize observability
init_observability()

# Load env
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Load NLP Models
logger.info("Loading SentenceTransformer model 'BAAI/bge-small-en-v1.5'...")
embedding_model = SentenceTransformer('BAAI/bge-small-en-v1.5')

logger.info("Loading spaCy model 'en_core_web_sm'...")
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.info("spaCy model 'en_core_web_sm' not found. Downloading...")
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def prepare_text(article: dict) -> str:
    # Prepend title for better semantic representation
    title = article.get("title") or ""
    body  = article.get("clean_text") or ""
    # bge-small-en-v1.5 performs best with this prefix
    return f"Represent this AI news article: {title}\n\n{body[:2000]}"

def get_smart_chunks(article: dict, tokenizer) -> list[str]:
    """
    Slices article's clean_text based on token counts to preserve semantic coherence.
    Each chunk is prepended with the standard query prefix and title context.
    """
    title = article.get("title") or ""
    body = article.get("clean_text") or ""
    
    # Tokenize the body to do exact token slicing
    body_tokens = tokenizer(body, truncation=False, add_special_tokens=False)["input_ids"]
    num_tokens = len(body_tokens)
    
    def make_chunk_text(body_part: str) -> str:
        return f"Represent this AI news article: {title}\n\n{body_part}"
        
    if num_tokens < 512:
        # Articles under 512 tokens -> embed as-is, one chunk, chunk_index=0
        return [prepare_text(article)]
        
    elif num_tokens <= 2000:
        # Articles 512–2000 tokens -> two chunks: first 512 + last 256 (title + conclusion signal)
        chunk0_ids = body_tokens[:512]
        chunk1_ids = body_tokens[-256:]
        
        chunk0_body = tokenizer.decode(chunk0_ids, skip_special_tokens=True)
        chunk1_body = tokenizer.decode(chunk1_ids, skip_special_tokens=True)
        
        return [
            prepare_text(article),
            make_chunk_text(chunk1_body)
        ]
        
    else:
        # Articles over 2000 tokens -> three chunks: intro, middle, conclusion (512 tokens each, 64-token overlap)
        chunk0_ids = body_tokens[:512]
        
        # Center the middle chunk
        mid_start = (num_tokens - 512) // 2
        chunk1_ids = body_tokens[mid_start : mid_start + 512]
        
        chunk2_ids = body_tokens[-512:]
        
        chunk1_body = tokenizer.decode(chunk1_ids, skip_special_tokens=True)
        chunk2_body = tokenizer.decode(chunk2_ids, skip_special_tokens=True)
        
        return [
            prepare_text(article),
            make_chunk_text(chunk1_body),
            make_chunk_text(chunk2_body)
        ]

def chunks_generator(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def process_batch(batch: list[dict]):
    """
    Processes a batch of articles:
    - Generates chunks and embeddings for each article
    - Extracts named entities using spaCy
    - Inserts embeddings into Supabase
    - Updates articles status to 'embedded' and stores entities
    """
    logger.info(f"Processing batch of {len(batch)} articles...")
    all_chunks_to_encode = []
    chunk_meta = []
    updates_to_run = []

    for article in batch:
        article_id = article["id"]
        clean_text = article.get("clean_text") or ""
        title = article.get("title") or ""

        # Use full title + clean text for entity extraction
        ner_text = f"{title}\n{clean_text}"
        # Cap text to 50k chars to avoid memory issues with huge pages in spaCy
        doc = nlp(ner_text[:50000])

        unique_entities = []
        seen_entities = set()
        for ent in doc.ents:
            text_cleaned = ent.text.strip()
            label = ent.label_
            if text_cleaned and (text_cleaned.lower(), label) not in seen_entities:
                seen_entities.add((text_cleaned.lower(), label))
                unique_entities.append({"text": text_cleaned, "label": label})

        # Chunk using smart token-based chunking strategy
        text_chunks = get_smart_chunks(article, embedding_model.tokenizer)
        for idx, chunk_txt in enumerate(text_chunks):
            all_chunks_to_encode.append(chunk_txt)
            chunk_meta.append({
                "article_id": article_id,
                "chunk_index": idx,
                "chunk_text": chunk_txt
            })

        updates_to_run.append((article_id, unique_entities))

    # Generate embeddings for all chunks in one model call
    all_embeddings_to_insert = []
    if all_chunks_to_encode:
        try:
            embeddings = embedding_model.encode(
                all_chunks_to_encode,
                batch_size=32,
                normalize_embeddings=True,  # Critical for cosine similarity
                show_progress_bar=False
            )
            for i, meta in enumerate(chunk_meta):
                all_embeddings_to_insert.append({
                    "article_id": meta["article_id"],
                    "chunk_index": meta["chunk_index"],
                    "chunk_text": meta["chunk_text"][:2000],  # Cap chunk text storage
                    "embedding": embeddings[i].tolist()
                })
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch: {e}")
            sentry_sdk.capture_exception(e)
            return

    # Bulk insert embeddings in one operation
    if all_embeddings_to_insert:
        try:
            logger.info(f"Inserting {len(all_embeddings_to_insert)} chunks into embeddings table...")
            supabase.table("embeddings").insert(all_embeddings_to_insert).execute()
        except Exception as e:
            logger.error(f"Failed to bulk insert embeddings: {e}")
            sentry_sdk.capture_exception(e)
            return

    # Update article status and entities
    for article_id, entities in updates_to_run:
        try:
            supabase.table("articles").update({
                "status": "embedded",
                "entities": entities
            }).eq("id", article_id).execute()
        except Exception as e:
            logger.error(f"Failed to update status/entities for article {article_id}: {e}")
            sentry_sdk.capture_exception(e)

def run_nlp():
    logger.info("Phase 2: NLP Embed & NER starting...")
    try:
        # Fetch up to 200 raw articles
        res = supabase.table("articles")\
            .select("id, clean_text, title")\
            .eq("status", "raw")\
            .not_.is_("clean_text", "null")\
            .limit(200)\
            .execute()
        
        articles = res.data or []
        logger.info(f"Found {len(articles)} raw articles to process.")
        
        if not articles:
            logger.info("No raw articles found with pending embeddings. Exiting.")
            return

        # Process in batches of 50
        processed_count = 0
        for batch in chunks_generator(articles, 50):
            process_batch(batch)
            processed_count += len(batch)

        logger.info(f"[SUCCESS] Processed and embedded {processed_count} articles.")

    except Exception as e:
        logger.error(f"NLP phase failed: {e}")
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_nlp()
