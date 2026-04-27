from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

# Load the model once (384 dimensions)
_model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_one(text: str) -> List[float]:
    """Generate embedding for a single text."""
    embedding = _model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts efficiently."""
    embeddings = _model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()
