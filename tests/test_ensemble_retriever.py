import os
import pytest
from dotenv import load_dotenv
from supabase import create_client
from llm.retriever import get_ensemble_retriever

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

@pytest.fixture
def supabase_client():
    assert SUPABASE_URL is not None
    assert SUPABASE_SERVICE_KEY is not None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def test_ensemble_retriever_queries(supabase_client):
    retriever = get_ensemble_retriever(supabase_client, match_count=3)
    
    # Define 20 test queries covering diverse categories (foundation models, agents, tools, funding, optimization, etc.)
    queries = [
        "transformer attention mechanisms",
        "agent workflows and LLM routing",
        "open source agent frameworks",
        "multimodal models vision audio",
        "major foundation model releases",
        "inference optimization sparse attention",
        "retrieval augmented generation RAG systems",
        "vector database indexing performance",
        "generative AI start-up funding rounds",
        "AI chip accelerators GPU TPU",
        "local language model fine-tuning",
        "evaluating LLM safety alignment",
        "reinforcement learning from human feedback RLHF",
        "prompt engineering techniques",
        "autonomous software engineering agents",
        "new model architectures state space models",
        "speculative decoding speedups",
        "distilling small language models",
        "data curation pipeline engineering",
        "robotic process automation with LLMs"
    ]
    
    assert len(queries) == 20
    
    print("\nRunning 20 EnsembleRetriever Test Queries:")
    for i, q in enumerate(queries, 1):
        try:
            results = retriever.invoke(q)
            print(f"[{i:02d}] Query: '{q}' -> Retrieved {len(results)} matches.")
            # Basic sanity check (should return list of Documents)
            assert isinstance(results, list)
            for doc in results:
                assert hasattr(doc, "page_content")
                assert isinstance(doc.metadata, dict)
        except Exception as e:
            # Note: HuggingFaceEmbeddings might take time or fail if network drops, 
            # but we catch and fail test explicitly to debug
            pytest.fail(f"Query '{q}' failed: {e}")
