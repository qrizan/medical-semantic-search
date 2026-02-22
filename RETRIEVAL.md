# RETRIEVAL.md
Catatan teknis proses retrieval di aplikasi FastAPI.

## Gambaran Umum

Sistem retrieval menggunakan dense embedding similarity search. Query di-encode menjadi vector, dibandingkan dengan corpus embeddings, lalu ranking dan lookup metadata untuk menampilkan hasil.

## Flow Diagram

```
User Query
    ↓
Query Encoding (HF Inference API)
    ↓
Normalized Vector
    ↓
Similarity Calculation (dot product)
    ↓
Scores
    ↓
Ranking (argsort descending)
    ↓
Top Indices
    ↓
Metadata Lookup
    ↓
Format & Display (HTML)
```

## Data Structure

**embeddings.npy**: Matrix embeddings untuk setiap chunk (L2-normalized). Digunakan untuk similarity calculation.

**metadata.json**: Array metadata untuk setiap chunk (teks + informasi artikel). Digunakan untuk menampilkan hasil.

**Index Mapping (Kritis)**: `metadata[i]` harus sesuai dengan `embeddings[i]`. Jika tidak match, hasil akan salah.

## Retrieval Process

1. **Query Encoding**: Query text di-encode via HuggingFace Inference API menjadi normalized vector
2. **Similarity Calculation**: Hitung cosine similarity via dot product antara query embedding dan semua corpus embeddings
3. **Ranking**: Ambil top-5 index dengan argsort descending berdasarkan score
4. **Metadata Lookup**: Ambil metadata chunk berdasarkan top indices
5. **Format & Display**: Format hasil (rank, title, snippet, score, chunk_id), hapus heading Mediawiki, potong di akhir kalimat terdekat, render via Jinja2

## Implementation

**engine.py**: Menangani proses retrieval - load data, encode query, hitung similarity, dan ranking hasil.

**main.py**: Menangani HTTP request, render template HTML, dan error handling.

## Performance

- Query encoding: ~200-500ms (network call ke HF API)
- Similarity: ~10-20ms (numpy dot product)
- Ranking: ~5ms (argsort)
- Total: ~250-550ms per query

## Catatan

- **Engine di-load sekali (singleton)** — tidak di-load setiap request, hanya saat pertama kali dipanggil
- **Query encoding via API** — tidak perlu download model ke server, menggunakan HuggingFace Inference API
- **Client dibuat per request** — menghindari stale connection setelah idle lama
- **Similarity di server** — menggunakan numpy dot product (cepat, ~10-20ms)
- **Stateless** — tidak ada session atau state, setiap request independen
- **Index mapping kritis** — metadata[i] harus sesuai dengan embeddings[i], jika tidak match hasil akan salah
