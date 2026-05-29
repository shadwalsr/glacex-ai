import sys

def verify():
    print("Verifying HuggingFace SentenceTransformer (bge-small-en-v1.5)...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        print("[SUCCESS] SentenceTransformer loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load SentenceTransformer: {e}")
        sys.exit(1)

    print("Verifying spaCy NER model (en_core_web_sm)...")
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("[SUCCESS] spaCy NER model loaded successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to load spaCy model: {e}")
        sys.exit(1)

    print("\n[SUCCESS] All models verified and ready!")

if __name__ == "__main__":
    verify()
