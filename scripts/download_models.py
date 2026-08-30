"""
Pre-download local AI models (e.g. sentence-transformers embeddings) for offline use.
"""

import sys

def download_models():
    print("Downloading embedding model: all-MiniLM-L6-v2...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        print("SentenceTransformer model downloaded successfully!")
    except Exception as e:
        print(f"Warning: Could not pre-download sentence-transformers model: {e}")
        print("It will be loaded on demand if sentence-transformers is installed.")

if __name__ == "__main__":
    download_models()
