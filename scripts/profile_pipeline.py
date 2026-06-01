import cProfile
import pstats
import io
import asyncio
import logging

# Configure minimal logs for profiling run
logging.basicConfig(level=logging.WARNING)

from agents.ingestion_agent import main_ingestion
from agents.nlp_agent import run_nlp
from agents.dedup_agent import run_dedup
from agents.llm_agent import run_llm_analysis
from agents.delivery_agent import run_delivery

def profile_phase(name, func, is_async=False):
    print(f"\n================ PROFILING PHASE: {name} ================")
    pr = cProfile.Profile()
    pr.enable()
    
    if is_async:
        asyncio.run(func())
    else:
        func()
        
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('tottime')
    ps.print_stats(15)  # print top 15 time consumers
    print(s.getvalue())

def main():
    print("Starting pipeline profiling pass...")
    
    # 1. Profile Ingestion (Async)
    try:
        profile_phase("Ingestion", main_ingestion, is_async=True)
    except Exception as e:
        print(f"Ingestion profile run skipped or failed: {e}")
        
    # 2. Profile NLP (Sync)
    try:
        profile_phase("NLP Processing", run_nlp, is_async=False)
    except Exception as e:
        print(f"NLP profile run skipped or failed: {e}")
        
    # 3. Profile Deduplication (Sync)
    try:
        profile_phase("Deduplication", run_dedup, is_async=False)
    except Exception as e:
        print(f"Deduplication profile run skipped or failed: {e}")
        
    # 4. Profile LLM Analysis (Sync wrapper)
    try:
        profile_phase("LLM Analysis", run_llm_analysis, is_async=False)
    except Exception as e:
        print(f"LLM Analysis profile run skipped or failed: {e}")
        
    # 5. Profile Delivery (Sync)
    try:
        profile_phase("Delivery & Telemetry", run_delivery, is_async=False)
    except Exception as e:
        print(f"Delivery profile run skipped or failed: {e}")

if __name__ == "__main__":
    main()
