import json
import re
import numpy as np
import os
import time
from pathlib import Path
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import logging

# load environment variables dari .env file
load_dotenv()

logger = logging.getLogger(__name__)

# global variables
_engine_data = None
CONFIG = None
embeddings = None
metadata = None

# Load embeddings dan metadata (hanya sekali, tidak berubah).
# client dibuat fresh setiap request untuk menghindari stale connection
def get_engine_data():
    global _engine_data, CONFIG, embeddings, metadata
    if _engine_data is None:
        artifacts_dir = Path("artifacts")

        # load config
        with open(artifacts_dir / "config.json", "r") as f:
            CONFIG = json.load(f)
        
        # load embeddings 
        embeddings = np.load(artifacts_dir / "embeddings.npy")
        
        # load metadata
        with open(artifacts_dir / "metadata.json", "r") as f:
            metadata = json.load(f)
        
        _engine_data = {
            "config": CONFIG,
            "embeddings": embeddings,
            "metadata": metadata
        }
    return _engine_data

# buat InferenceClient baru dengan timeout.
def create_client():
    return InferenceClient(
        provider="hf-inference",
        api_key=os.environ.get("HF_TOKEN"),
        timeout=20.0  # 20 detik timeout
    )

# bersihkan teks chunk untuk ditampilkan sebagai snippet.   
#   - hapus heading Mediawiki (== Judul ==, === Sub ===, dst.)
#   - potong di akhir kalimat terdekat agar tidak terpotong di tengah.
def clean_snippet(text: str, max_chars: int = 450) -> str:

    # hapus heading Mediawiki: == ... ==  /  === ... ===  dst.
    text = re.sub(r'={1,4}[^=\n]+={1,4}', '', text)
    # kolapskan whitespace berlebih
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= max_chars:
        return text

    # cari titik terakhir sebelum batas karakter
    truncated = text[:max_chars]
    last_period = truncated.rfind('. ')
    # gunakan titik hanya jika cukup jauh dari awal (hindari potong terlalu pendek)
    if last_period > max_chars // 2:
        return truncated[:last_period + 1]
    return truncated

# semantic search dengan client baru setiap request untuk menghindari stale connection.
def semantic_search(query: str, top_k: int = None):
    # load engine data (embeddings, metadata) - hanya sekali
    engine_data = get_engine_data()
    CONFIG = engine_data["config"]
    embeddings = engine_data["embeddings"]
    metadata = engine_data["metadata"]
    
    # ambil top_k dari config jika None
    if top_k is None:
        top_k = CONFIG["top_k"]
    
    # buat client baru setiap request (menghindari stale connection)
    client = create_client()
    
    # encode query via Inference API dengan retry logic
    max_retries = 2
    q_emb = None
    
    for attempt in range(max_retries):
        try:
            q_emb = client.feature_extraction(
                query,
                model=CONFIG["model_name"]
            )
            q_emb = np.array(q_emb)
            break  # Success, keluar dari loop
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:

                # buat client baru untuk retry
                client = create_client()
                time.sleep(0.5)  # Tunggu sebentar sebelum retry
            else:
                # semua retry gagal
                logger.error(f"All {max_retries} attempts failed")
                raise Exception(f"Gagal menghubungi HuggingFace API setelah {max_retries} percobaan: {str(e)}")
    
    # normalize query embedding 
    # karena corpus embeddings sudah normalized
    q_emb = q_emb / np.linalg.norm(q_emb)
    
    # cosine similarity via dot product (tetap di server)
    scores = np.dot(embeddings, q_emb)
    
    # ambil top_k index
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    results = []
    
    for rank, idx in enumerate(top_indices, start=1):
        chunk = metadata[idx]
        
        snippet = clean_snippet(chunk["text"])
        
        results.append({
            "rank": rank,
            "article_title": chunk["article_title"],
            "snippet": snippet,
            "score": float(scores[idx]),
            "chunk_id": chunk["chunk_id"]
        })
    
    return results