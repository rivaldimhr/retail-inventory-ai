# AIforBusiness - Retail Inventory Optimization System

## 🌟 Pendahuluan
AIforBusiness adalah solusi analitik berbasis AI yang dirancang untuk membantu bisnis ritel mengoptimalkan manajemen inventaris. Sistem ini mengintegrasikan **Machine Learning (XGBoost)** untuk prediksi permintaan, **Market Basket Analysis (MBA)** untuk memahami pola pembelian konsumen, dan **Large Language Model (LLM)** untuk memberikan rekomendasi strategis melalui antarmuka chat.

Tujuan utama sistem ini adalah menekan biaya operasional dengan meminimalkan *overstock* (stok berlebih) dan mencegah *stockout* (kehabisan stok) menggunakan data historis transaksi.

---

## 🏗️ Arsitektur Sistem
Sistem ini menggunakan pola **Service-Layer-Repository (SLR)** untuk memastikan pemisahan tanggung jawab yang jelas dan skalabilitas tinggi.

- **Frontend**: React (TypeScript) + Vite + Recharts.
- **Backend**: FastAPI (Python) + Uvicorn.
- **ML Engine**: XGBoost (Time-series forecasting).
- **MBA Engine**: Apriori & Association Rules (mlxtend).
- **LLM Engine**: Natural Language Processing untuk ringkasan stok dan rekomendasi (Context-aware).

---

## 🛠️ Prasyarat Instalasi

### 1. Backend (Python)
Pastikan Anda memiliki Python 3.9+.
```bash
# Buat virtual environment (opsional tapi disarankan)
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Frontend (React)
Pastikan Anda memiliki Node.js 18+.
```bash
# Masuk ke root directory
npm install
```

---

## 🚀 Alur Kerja Sistem (System Flow)

Sistem beroperasi melalui empat fase utama:

### 1. Data Pipeline (Pre-processing)
- **Cleaning**: Membersihkan data transaksi mentah (`Groceries_dataset.csv`).
- **Reindexing**: Mengubah transaksi menjadi deret waktu harian (Daily Time-series).
- **Stock Simulation**: Mensimulasikan tingkat stok berdasarkan penjualan historis dan parameter reorder point.
- **Feature Engineering**: Membuat fitur pendukung ML seperti *rolling sales*, tren mingguan, dan fitur kalender (hari libur nasional).

### 2. ML Engine (Forecasting)
- **Training**: Melatih model XGBoost menggunakan data fitur yang telah diproses.
- **Prediction**: Menghasilkan prediksi permintaan untuk periode mendatang.
- **Risk Flagging**: Memberikan label otomatis pada produk yang berisiko (Stockout, Overstock, Deadstock).

### 3. Market Basket Analysis (Insight Penjualan)
- Menjalankan algoritma Apriori untuk menemukan hubungan antar produk (misal: Pelanggan yang membeli "Milk" cenderung membeli "Bread").
- Menghasilkan aturan asosiasi (*Support, Confidence, Lift*) untuk strategi *cross-selling*.

### 4. Integration & UI
- **API Endpoints**: Menyediakan data prediksi dan MBA ke Dashboard.
- **LLM Chat**: Mengambil konteks inventaris (produk berisiko tinggi) untuk menjawab pertanyaan pengguna secara natural.

---

## 💡 Use Cases (Kasus Penggunaan)

### Case 1: Pencegahan Stockout (Kehabisan Stok)
**Masalah**: Toko sering kehilangan potensi penjualan karena produk populer habis sebelum jadwal pengiriman berikutnya.
**Solusi**: Sistem mendeteksi `stockout_risk` jika `coverage_days < lead_time`. Dashboard memberikan peringatan merah agar manajer segera melakukan *Restock*.

### Case 2: Reduksi Overstock & Deadstock
**Masalah**: Modal tertahan di gudang karena stok produk yang tidak laku menumpuk.
**Solusi**: Sistem memberikan flag `overstock_risk` (stok > 30 hari) atau `deadstock_risk` (tidak ada penjualan signifikan). Manajer dapat merencanakan promo atau diskon untuk produk tersebut.

### Case 3: Optimasi Bundle Produk (Cross-Selling)
**Masalah**: Kurangnya strategi promosi yang berbasis data.
**Solusi**: Menggunakan output **MBA** untuk membuat paket *bundling*. Jika data menunjukkan korelasi kuat antara "Sosis" dan "Saus", toko bisa meletakkan keduanya berdekatan atau membuat harga paket hemat.

### Case 4: Konsultasi Strategis via AI Chat
**Masalah**: Manajer toko kesulitan membaca tabel data yang kompleks.
**Solusi**: Manajer bertanya ke AI: *"Produk apa yang harus saya pesan hari ini?"*. AI akan menganalisis `inventory_context` dan menjawab: *"Anda harus memesan Produk A karena stok hanya cukup untuk 2 hari ke depan."*

---

## 🖥️ Cara Menjalankan Sistem

### Langkah 1: Siapkan Data
Letakkan file `Groceries_dataset.csv` di dalam folder `data/`.

### Langkah 2: Jalankan Pipeline Awal
Gunakan Orchestrator untuk memproses data dan melatih model pertama kali.
```bash
$env:PYTHONPATH = "."; python src/controllers/orchestrator.py
```

### Langkah 3: Jalankan Backend API
```bash
$env:PYTHONPATH = "."; uvicorn src.api.main:app --reload
```
API akan tersedia di `http://127.0.0.1:8000`. Dokumentasi Swagger di `/docs`.

### Langkah 4: Jalankan Frontend Dashboard
```bash
npm run dev
```
Buka `http://localhost:5173` di browser Anda.

---

## 📡 Dokumentasi API Utama

- `GET /api/v1/forecast`: Mengambil semua hasil prediksi dan risk flags.
- `GET /api/v1/mba`: Mengambil hasil analisis asosiasi produk.
- `POST /api/v1/chat`: Mengirim pesan ke AI dengan konteks stok terbaru.
- `POST /api/v1/forecast/refresh`: Menjalankan ulang seluruh pipeline (Data -> ML).

---

## 📁 Struktur Proyek
```text
D:\AIforBusiness\
├── data/               # Penyimpanan dataset mentah, model, dan hasil JSON
├── notebooks/          # Eksperimen EDA dan evaluasi model (Jupyter)
├── src/
│   ├── api/            # Server FastAPI dan definisi routes
│   ├── config/         # Konfigurasi path dan variabel sistem
│   ├── controllers/    # Orchestrator alur kerja utama
│   ├── data_pipeline/  # Logika pembersihan dan feature engineering
│   ├── dashboard/      # Frontend React & Visualisasi
│   ├── llm_engine/     # Integrasi LLM dan Prompt Engineering
│   ├── repositories/   # Abstraksi akses file/database
│   └── services/       # Logika bisnis (ML, MBA, Simulation)
└── requirements.txt    # Daftar library Python
```

---
**Pengembang**: Bastian Natanael Sibarani
**Status Proyek**: Aktif (Workload A-D Selesai, Workload E dalam pengembangan)
