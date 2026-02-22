# MODELING.md
Catatan teknis proyek Medical Semantic Search — ringkasan dari notebook 00–07.

## Gambaran Umum

Sistem semantic search berbasis dense retrieval untuk artikel kesehatan Wikipedia bahasa Indonesia.
Pipeline: data acquisition → chunking → embedding → retrieval → evaluasi → export.

- **Model**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Embedding dim**: 384
- **Similarity**: cosine via dot product (embedding di-normalize L2 secara offline)
- **Top-K**: 5
- **Storage**: Google Drive + numpy (tanpa vector database)

## Pipeline

### 00 — Project Setup
Inisialisasi config global, seed, dan path proyek.

Config yang dipakai di seluruh pipeline:
```
model_name           : sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
top_k                : 5
overlap_tokens       : 75
max_articles         : 500
min_paragraph_tokens : 40
embedding_dim        : 384
seed                 : 42
```

### 01 — Data Acquisition
Scraping artikel Wikipedia Indonesia via Search API berdasarkan keyword medis. Filter minimal: panjang teks ≥ 500 karakter. Output: `data/raw_articles.json` (data freeze).

### 02 — Text Chunking
Chunking berbasis paragraf dengan adjacent overlap. Strategi: split teks per `\n`, paragraf pendek (< 40 whitespace token) digabung ke paragraf berikutnya, setiap chunk ditambahkan 75 token terakhir dari paragraf sebelumnya sebagai overlap. Output: `data/chunks.json`.

### 03 — Embedding Generation
Encode seluruh chunk menggunakan SentenceTransformer dengan `batch_size=64`. L2 normalization dilakukan manual secara offline (bukan saat encode) agar retrieval cukup pakai dot product. Output: `artifacts/embeddings.npy` (float32), `artifacts/metadata.json`.

### 04 — Retrieval Engine
Implementasi fungsi `semantic_search(query, top_k)`: encode query dengan normalize, hitung cosine similarity via dot product, ambil top-K index dengan argsort. Output: rank, article_title, snippet, score, chunk_id. Di aplikasi FastAPI, snippet diproses dengan `clean_snippet()` untuk menghapus heading Mediawiki dan memotong di akhir kalimat (max 450 karakter).

### 05 — Exploratory Testing
Pengujian kualitatif sebelum evaluasi formal: query umum, query spesifik, analisis distribusi skor untuk mengevaluasi diskriminatif model.

### 06 — Retrieval Evaluation
Evaluasi dengan ground truth yang ditentukan manual. Metrik: Top-1 Accuracy, Top-3 Accuracy, Recall@5, MRR. Output: `artifacts/evaluation_results.json`.

### 07 — Model Freeze and Export
Verifikasi konsistensi seluruh artifact sebelum di-freeze: jumlah embedding vs metadata, dimensi embedding, L2 normalization, evaluation set lengkap. Output: `artifacts/retrieval_module.py`, `artifacts/project_summary.json`.

## Artifact yang Dihasilkan

```
data/
├── raw_articles.json       # artikel Wikipedia (frozen)
└── chunks.json             # chunk hasil chunking

artifacts/
├── config.json             # konfigurasi global
├── embeddings.npy          # matrix embeddings float32, L2-normalized
├── metadata.json           # metadata per chunk
├── evaluation_set.json     # query + ground truth
├── evaluation_results.json # metrik per query + agregat
├── retrieval_module.py     # modul inference reusable
└── project_summary.json    # ringkasan final (status: FROZEN)
```

## Catatan

- Pipeline ini adalah **dense retrieval baseline** murni — tidak ada BM25, hybrid, re-ranking, atau fine-tuning.
- Redundansi artikel dalam Top-5 adalah konsekuensi wajar dari paragraph-based chunking.
