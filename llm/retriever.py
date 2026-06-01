import os
import re
from datetime import datetime, timedelta
from typing import List
from supabase import Client
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun

def tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())

class SupabasePGVectorRetriever(BaseRetriever):
    client: Client
    embeddings: HuggingFaceEmbeddings
    match_count: int = 5

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        # Generate the query embedding using BAAI/bge-small-en-v1.5
        query_vector = self.embeddings.embed_query(query)
        
        # Call match_documents RPC directly via Supabase client
        res = self.client.rpc("match_documents", {
            "query_embedding": query_vector,
            "match_threshold": 0.0,
            "match_count": self.match_count
        }).execute()
        
        results = res.data or []
        
        docs = []
        for r in results:
            docs.append(Document(
                page_content=r.get("content") or "",
                metadata=r.get("metadata") or {}
            ))
        return docs

def get_ensemble_retriever(supabase_client: Client, match_count: int = 5) -> EnsembleRetriever:
    """
    Creates a LangChain EnsembleRetriever combining Supabase Vector store (pgvector)
    and an in-memory BM25Retriever built from articles scraped in the last 7 days.
    """
    # 1. Initialize Embeddings Model (using the bge-small-en-v1.5 model)
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    # 2. Initialize Custom Supabase Vector Store Retriever
    pgvector_retriever = SupabasePGVectorRetriever(
        client=supabase_client,
        embeddings=embeddings,
        match_count=match_count
    )

    # 3. Retrieve last 7 days of articles to build the BM25 corpus
    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    res = supabase_client.table("articles")\
        .select("id, title, clean_text, url, published_at")\
        .gt("scraped_at", seven_days_ago)\
        .execute()
        
    articles = res.data or []
    
    # 4. Construct LangChain Documents for BM25
    documents = []
    for a in articles:
        content = a.get("clean_text") or a.get("title") or ""
        if content.strip():
            doc = Document(
                page_content=content,
                metadata={
                    "article_id": a["id"],
                    "title": a.get("title") or "",
                    "url": a.get("url") or "",
                    "published_at": a.get("published_at") or ""
                }
            )
            documents.append(doc)

    # Handle edge case where no articles exist in the last 7 days
    if not documents:
        documents = [
            Document(
                page_content="No recent articles found in the database corpus.",
                metadata={"title": "System Placeholder", "url": "", "article_id": ""}
            )
        ]

    # Initialize BM25Retriever with custom tokenizer
    bm25_retriever = BM25Retriever.from_documents(
        documents=documents,
        preprocess_func=tokenize
    )
    bm25_retriever.k = match_count

    # 5. Build EnsembleRetriever
    ensemble_retriever = EnsembleRetriever(
        retrievers=[pgvector_retriever, bm25_retriever],
        weights=[0.6, 0.4]
    )

    return ensemble_retriever
