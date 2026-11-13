# Retail Inventory AI

[![CI](https://github.com/rivaldimhr/retail-inventory-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/rivaldimhr/retail-inventory-ai/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Data](https://img.shields.io/badge/data-Online%20Retail%20II%20(UCI)-4f46e5)

**🔗 Demo online: https://rivaldimhr.github.io/retail-inventory-ai/** (tanpa install, data asli)

![Dashboard Retail Inventory AI](docs/screenshot-dashboard.png)

> **Status Chat AI:** di demo online, Chat AI **belum berjalan dengan model AI**. Saat ini chat hanya berjalan dalam **mode demo** (menjawab otomatis dari data), karena API key LLM perlu disiapkan terlebih dahulu. Semua kode dan konfigurasi untuk mengaktifkannya sudah tersedia. Lihat [Mengaktifkan Chat AI](#-mengaktifkan-chat-ai).

Sistem analitik berbasis AI untuk membantu toko ritel mengelola stok. Sistem ini menjawab empat pertanyaan yang sering dihadapi manajer toko:

| Pertanyaan manajer | Cara sistem menjawab |
|---|---|
| Berapa banyak setiap produk akan terjual minggu depan? | **Prediksi permintaan 7 hari** dengan model gradient boosting |
| Produk mana yang harus dipesan hari ini, dan berapa unit? | **Rekomendasi pesan** dari prediksi, stok, dan waktu kirim supplier |
| Produk apa yang sering dibeli bersamaan? | **Market basket analysis** dari invoice asli |
| "Kenapa produk ini berisiko?" | **Chat AI** yang membaca kondisi stok terbaru |

Tujuannya: mencegah **kehabisan stok (stockout)** yang membuat penjualan hilang, dan mengurangi **stok berlebih (overstock)** yang menahan modal.

> Dikembangkan ulang dari proyek kelompok mata kuliah AI for Business, Institut Teknologi Bandung (2026). Lihat [Asal Proyek](#-asal-proyek).

---

## 📊 Dataset

Proyek ini memakai **[Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)** dari UCI Machine Learning Repository (lisensi **CC BY 4.0**).

- Transaksi asli sebuah toko online di Inggris yang menjual barang hadiah dan perlengkapan rumah, periode **1 Desember 2009 – 9 Desember 2011**.
- Sekitar **1,07 juta baris**. Kolom: `Invoice`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `Price`, `Customer ID`, `Country`.
- Banyak pelanggannya adalah pedagang grosir, jadi sesekali ada pesanan dalam jumlah sangat besar.

**Kenapa dataset ini:**
1. Ada **jumlah unit** dan **harga**, sehingga prediksi bisa dinyatakan dalam unit sekaligus nilai uang (£).
2. Ada **nomor invoice**, sehingga market basket memakai keranjang belanja yang sesungguhnya.
3. Lisensinya terbuka, sehingga hasilnya boleh dipublikasikan.

Sitasi: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

---

## 🧱 Teknologi

| Lapisan | Teknologi |
|---|---|
| Frontend | React 18, TypeScript, Vite, Recharts |
| Backend | FastAPI, Uvicorn |
| Prediksi permintaan | Gradient boosting (scikit-learn HistGradientBoosting, loss Poisson); XGBoost opsional lewat `MODEL=xgboost` |
| Market basket | Aturan asosiasi dua produk (support, confidence, lift) dengan matriks sparse SciPy |
| Chat AI | API apa pun yang kompatibel dengan OpenAI (bawaan: Groq, Llama 3.1 8B; bisa Gemini, OpenAI, Ollama). **Belum aktif di demo**, perlu API key |
| Data | pandas, NumPy, holidays |
| Kualitas | pytest, GitHub Actions |

---

## 📈 Hasil pada Data Asli

Dijalankan pada Online Retail II lengkap: **1.003.214 baris transaksi bersih, 39.516 invoice, 4.707 produk**. Prediksi dibuat untuk 300 produk terlaris.

**Akurasi prediksi 7 hari** (data uji 2011-10-07 s.d. 2011-12-01, yaitu musim puncak menjelang Natal):

| Metode | MAE (unit/produk/minggu) | WAPE | Bias |
|---|---|---|---|
| **Model (gradient boosting, Poisson)** | **91.0** | **46.4%** | **-2.3%** |
| Rata-rata 28 hari × 7 | 93.0 | 47.4% | -6.3% |
| Sama dengan 7 hari terakhir | 107.7 | 54.9% | -1.9% |

- Model **2.2% lebih akurat (MAE)** dari metode pembanding terbaik (rata-rata 28 hari), dan biasnya juga lebih kecil, artinya prediksinya tidak cenderung terlalu rendah. Ini penting untuk stok: prediksi yang terlalu rendah membuat barang cepat habis. Metode "sama dengan 7 hari terakhir" memang biasnya paling kecil, tetapi meleset jauh lebih besar (MAE 108).
- Selisihnya kecil karena permintaan toko ini sangat tidak teratur: banyak pembeli grosir yang sesekali memesan dalam jumlah besar. WAPE sekitar 46% menunjukkan bahwa permintaan mingguan per produk memang sulit ditebak, sehingga stok pengaman tetap diperlukan.
- Model dengan target log sempat diuji dan MAE-nya sedikit lebih kecil, tetapi biasnya sekitar −20%. Model itu tidak dipakai karena akan membuat toko kekurangan stok.
- Hari terakhir dataset (9 Desember 2011) hanya berisi transaksi setengah hari, jadi otomatis diabaikan. Data dianggap berakhir pada 8 Desember 2011.

**Akurasi dalam persen** (akurasi = 100% − WAPE, yaitu total selisih prediksi dibagi total penjualan sebenarnya):

| Metode | Akurasi | Rata-rata meleset per produk/minggu |
|---|---|---|
| **Model (gradient boosting)** | **53.6%** | **91.0 unit** |
| Rata-rata 28 hari | 52.6% | 93.0 unit |
| Sama dengan 7 hari terakhir | 45.1% | 107.7 unit |

<details>
<summary>Akurasi per kategori</summary>

| Kategori | Akurasi |
|---|---|
| Christmas & seasonal | 69.9% |
| Garden | 68.5% |
| Accessories & warmers | 58.9% |
| Bags & storage | 57.2% |
| Stationery & gift wrap | 53.0% |
| Kitchen & dining | 52.3% |
| Other | 47.6% |
| Baking & party | 47.5% |
| Home decor | 46.8% |
| Candles & lighting | 46.2% |
| Toys & games | 44.4% |

</details>

**Cara membaca angka ini:**
- **Per produk per minggu**, prediksi rata-rata meleset sekitar 46%. Ini wajar untuk toko dengan banyak pembeli grosir: satu pesanan besar bisa melipatgandakan penjualan satu produk dalam seminggu, dan itu tidak bisa ditebak dari data masa lalu.
- **Untuk total semua produk**, prediksi hanya meleset 2.3% (bias -2.3%). Gambaran besarnya hampir tepat; yang sulit ditebak adalah naik-turun per produk.
- Karena itu sistem tetap memakai **stok pengaman** untuk menutup ketidakpastian per produk.

**Contoh pasangan produk dari market basket** (setiap pasangan ditampilkan sekali, ke arah yang paling kuat): pembeli *Coffee Mug Dog + Ball Design* 75% juga membeli *Coffee Mug Cat + Bird Design* (lift 46). Produk seri *Poppy's Playhouse* (bedroom, living room, kitchen) juga hampir selalu dibeli bersamaan.

---

## 🔄 Alur Kerja Sistem

Sistem punya dua alur: **pipeline**, yang mengolah data dan melatih model, dan **runtime**, yang berjalan saat dashboard dipakai.

### 1. Pipeline: dari data mentah ke rekomendasi

```mermaid
flowchart TD
    A[("Online Retail II<br/>invoice asli")] --> B["Pembersihan data<br/>buang pembatalan, ongkir, biaya"]
    B --> C["Penjualan harian<br/>300 produk terlaris"]
    B --> M["Market basket<br/>1 invoice = 1 keranjang"]
    C --> D["Simulasi stok<br/>titik pesan ulang + stok pengaman"]
    D --> E["Fitur prediksi<br/>hanya data masa lalu"]
    E --> F["Evaluasi model<br/>vs metode rata-rata"]
    E --> G["Prediksi 7 hari ke depan"]
    G --> H["Keputusan per produk<br/>saran pesan, nilai berisiko, label risiko"]
    H --> J[("forecast_results.json")]
    F --> K[("model_metrics.json")]
    M --> N[("mba_results.json")]
```

| Tahap | Yang dilakukan | Kode |
|---|---|---|
| **Pembersihan** | Membuang invoice pembatalan (diawali `C`), jumlah atau harga ≤ 0, dan kode non-produk seperti ongkos kirim (`POST`), biaya bank, dan penyesuaian manual. Setiap produk diberi satu nama baku. | `src/data_pipeline/loader.py` |
| **Penjualan harian** | Menghitung unit terjual per hari untuk **300 produk yang paling sering dipesan**. Hari tanpa penjualan diisi 0, dan hari terakhir yang datanya hanya setengah hari diabaikan. Pesanan grosir yang ekstrem dibatasi di persentil ke-99 supaya tidak merusak model. Kategori produk dibuat dari kata kunci pada nama produk. | `src/data_pipeline/pipeline.py` |
| **Simulasi stok** | Dataset hanya berisi penjualan, jadi stok disimulasikan dengan kebijakan *reorder point* yang lazim dipakai toko (lihat [Simulasi Stok](#-simulasi-stok)). | `src/services/stock_simulation.py` |
| **Fitur** | Rata-rata 7/14/28/56 hari, variasi permintaan, hari sejak penjualan terakhir, tren, harga, bulan, jarak ke Natal, dan hari libur Inggris pada minggu berikutnya. Semua fitur hanya memakai data sampai hari itu. | `src/services/feature_service.py` |
| **Evaluasi** | 8 minggu terakhir disisihkan sebagai data uji. Model dibandingkan dengan dua metode sederhana: "sama seperti 7 hari terakhir" dan "rata-rata 28 hari". | `src/services/ml_service.py` |
| **Prediksi** | Model dilatih ulang dengan semua data, lalu memprediksi **total penjualan 7 hari ke depan** untuk setiap produk. | `src/services/ml_service.py` |
| **Keputusan** | Menghitung stok pengaman, titik pesan ulang, saran jumlah pesan, nilai penjualan yang berisiko hilang, dan label risiko. | `src/services/inventory_service.py` |
| **Market basket** | Mencari pasangan produk yang sering muncul di invoice yang sama. | `src/services/mba_service.py` |

Semua tahap dijalankan berurutan oleh `src/controllers/orchestrator.py`.

### 2. Runtime: saat dashboard dipakai

```mermaid
flowchart LR
    U["Manajer toko<br/>(browser)"] --> R["React dashboard"]
    R --> API["FastAPI backend"]
    API --> J[("Hasil JSON<br/>cache 1 jam")]
    API --> L["Model AI<br/>(Groq / Gemini / Ollama)"]
```

| Fitur di dashboard | Endpoint API | Yang terjadi |
|---|---|---|
| Tab **Stok & Prediksi** | `GET /api/v1/forecast` | Semua produk beserta prediksi, saran pesan, nilai berisiko, dan label risiko |
| Klik satu produk | `GET /api/v1/products/{id}/history` | Grafik penjualan, stok, dan penjualan yang hilang 90 hari terakhir |
| Kotak akurasi model | `GET /api/v1/forecast` (bagian `metadata.model`) | Ringkasan akurasi; evaluasi lengkap per kategori ada di `GET /api/v1/metrics` |
| Tab **Market Basket** | `GET /api/v1/mba` | Pasangan "beli A → cenderung beli B" |
| Tombol **Hitung ulang** | `POST /api/v1/mba/refresh` | Menghitung ulang market basket |
| **Chat AI** | `POST /api/v1/chat` | Pertanyaan + ringkasan stok + data produk yang disebut di pertanyaan dikirim ke model AI |
| Status server | `GET /api/v1/health` | Apakah data sudah ada, sudah usang, dan apakah Chat AI sudah dikonfigurasi |
| Perbarui prediksi | `POST /api/v1/forecast/refresh` | Melatih ulang model (`?rebuild_data=true` untuk membaca ulang dataset) |

Dokumentasi interaktif tersedia di `http://127.0.0.1:8000/docs` saat backend berjalan.

---

## 📦 Simulasi Stok

Online Retail II tidak punya data stok, jadi stok disimulasikan dengan kebijakan yang bisa dipakai toko sungguhan:

| Parameter | Nilai |
|---|---|
| Waktu kirim supplier | 3, 5, 7, atau 10 hari, tetap per produk |
| Stok pengaman | 1,65 × simpangan baku permintaan harian × √waktu kirim (≈ tingkat layanan 95%) |
| Titik pesan ulang | rata-rata permintaan harian × waktu kirim + stok pengaman |
| Jumlah pesan | cukup untuk waktu kirim + 14 hari + stok pengaman, dikurangi stok dan barang yang sedang dikirim |

Rata-rata dan simpangan baku hanya memakai 28 hari terakhir, jadi simulasi tidak pernah "melihat masa depan". Permintaan yang datang saat stok kosong dicatat sebagai **penjualan hilang**.

**Arti label risiko di dashboard:**

| Label | Kapan muncul | Saran tindakan |
|---|---|---|
| **Stok kosong** | Stok di rak saat ini 0, walaupun mungkin ada kiriman yang sedang dalam perjalanan | Penjualan sedang hilang; percepat kiriman jika bisa |
| **Stockout** | Stok + barang yang sedang dikirim tidak cukup sampai kiriman berikutnya tiba | Pesan hari ini sesuai kolom *Saran pesan* |
| **Overstock** | Stok cukup untuk lebih dari 60 hari | Tunda pemesanan |
| **Deadstock** | Tidak terjual sama sekali selama 60 hari, tapi masih ada stok | Diskon atau cuci gudang |
| **Promo** | Penjualan turun dan stok masih cukup untuk lebih dari 30 hari | Pertimbangkan promosi |
| **Lost Sales** | Ada permintaan yang tidak terlayani dalam 30 hari terakhir | Tambah stok pengaman |

---

## 🚀 Instalasi

### Prasyarat
- Python 3.10 atau lebih baru
- Node.js 18 atau lebih baru
- (Opsional) API key LLM untuk Chat AI. Groq dan Gemini punya tier gratis.

### Langkah 1: Clone dan install

```bash
git clone https://github.com/rivaldimhr/retail-inventory-ai.git
cd retail-inventory-ai

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

npm install
```

### Langkah 2: Unduh dataset
1. Buka https://archive.ics.uci.edu/dataset/502/online+retail+ii dan klik **Download**.
2. Ekstrak, lalu simpan file `online_retail_II.xlsx` di folder `data/`.

Versi CSV (misalnya dari Kaggle) juga bisa dipakai: simpan di `data/` dan isi `RAW_DATA_PATH` di `.env`.

### Langkah 3: Atur konfigurasi

```bash
cp .env.example .env
```

Isi `LLM_API_KEY` untuk mengaktifkan Chat AI. Contoh pengaturan Groq, Gemini, OpenAI, dan Ollama ada di dalam `.env.example`. Tanpa API key, dashboard tetap berjalan normal dan Chat AI akan menampilkan cara mengaktifkannya.

### Langkah 4: Jalankan pipeline

```bash
python -m src.controllers.orchestrator
```

Membaca file `.xlsx` butuh sekitar 1–2 menit. Hasilnya tersimpan di folder `data/`: transaksi bersih, penjualan harian, model, prediksi, hasil evaluasi, dan market basket.

### Langkah 5: Jalankan backend dan frontend

```bash
# Terminal 1: backend (http://127.0.0.1:8000)
uvicorn src.api.main:app --reload

# Terminal 2: frontend (http://localhost:5173)
npm run dev
```

Buka **http://localhost:5173** di browser.

### Menjalankan test

```bash
python -m pytest -q
```

Test memakai data tiruan berformat Online Retail II (`tests/fake_data.py`), jadi tidak perlu mengunduh dataset. Test yang sama berjalan otomatis di GitHub Actions setiap ada push.

---

## 🌐 Mode Demo

Demo online berjalan tanpa server. Dashboard membaca hasil pipeline yang disimpan sebagai file JSON di `public/demo/`.

```bash
python -m src.controllers.orchestrator   # jalankan pipeline dengan dataset asli
python scripts/export_demo.py            # simpan hasilnya ke public/demo/*.json
VITE_DEMO=true npm run build             # build dashboard versi demo ke folder dist/
```

Setiap push ke `main`, GitHub Actions membangun versi demo dan menyimpannya di branch `gh-pages`.

Di mode demo, Chat AI menjawab otomatis dari data dengan aturan sederhana (misalnya daftar produk yang perlu dipesan). Setiap jawaban diberi keterangan bahwa model AI belum aktif.

---

## 🤖 Mengaktifkan Chat AI

> **Status saat ini:** Chat AI **belum berjalan** di demo online. Integrasinya sudah selesai dan sudah dites, tetapi butuh **API key LLM** yang harus dibuat dengan akun sendiri.

**Di komputer sendiri (paling cepat):**
1. Buat API key gratis di [Groq](https://console.groq.com/keys) (tanpa kartu kredit), atau di Google AI Studio untuk Gemini.
2. Isi `LLM_API_KEY` di file `.env` (contoh pengaturan ada di `.env.example`).
3. Jalankan backend dan frontend seperti di bagian [Instalasi](#-instalasi). Chat akan menjawab memakai model AI sambil membaca data stok.

**Online, supaya demo memakai AI sungguhan:**

| Pilihan | File | Catatan |
|---|---|---|
| **Hugging Face Spaces** (disarankan) | `Dockerfile`, `.github/workflows/deploy-hf.yml` | Gratis tanpa kartu. Isi secret `HF_TOKEN` dan variable `HF_SPACE` di GitHub, lalu `LLM_API_KEY` di pengaturan Space |
| Render | `render.yaml` | Paket gratis, tetapi Blueprint meminta kartu pembayaran |
| Docker di server mana pun | `Dockerfile` | `docker build -t retail-api . && docker run -p 7860:7860 -e LLM_API_KEY=... retail-api` |

Setelah backend online, isi repository variable `CHAT_API_URL` di GitHub dengan alamat backend tersebut. Build demo berikutnya akan otomatis memakai Chat AI sungguhan.

Pengaman yang sudah ada:
- API key tidak pernah disimpan di kode.
- Batas 10 pertanyaan per menit per pengunjung dan maksimal 500 karakter per pesan, supaya kuota gratis tidak habis.
- Server tidak membutuhkan dataset, karena otomatis memakai hasil di `public/demo/`.
- Jika server AI sedang tidur atau tidak bisa dihubungi, chat di demo tetap menjawab dari data.

---

## 🖼️ Tampilan

| Market Basket | Tampilan HP |
|---|---|
| ![Market basket](docs/screenshot-market-basket.png) | ![Tampilan HP](docs/screenshot-mobile.png) |

---

## 🗺️ Diagram Aktivitas Pengguna

Diagram ini menunjukkan langkah yang dilakukan pengguna (manajer toko atau staf gudang) setiap kali memakai sistem. Penjelasan detail setiap langkah ada di [Panduan Pengguna](#-panduan-pengguna).

### A. Rutinitas harian: cek stok sampai ambil keputusan

```mermaid
flowchart TD
    S(("Mulai")) --> A["Buka dashboard"]
    A --> B["Lihat kartu ringkasan:<br/>perlu dipesan, risiko kehabisan,<br/>nilai berisiko"]
    B --> C{"Ada produk yang<br/>perlu dipesan?"}
    C -- Ya --> D["Centang 'Hanya yang perlu dipesan'"]
    D --> E["Klik produk untuk cek grafik<br/>penjualan dan stok"]
    E --> E2["Unduh daftar pesan (CSV)<br/>dan kirim ke supplier"]
    E2 --> F
    C -- Tidak --> F{"Ada produk<br/>overstock atau deadstock?"}
    F -- Ya --> G["Tunda pemesanan<br/>atau rencanakan diskon"]
    G --> H
    F -- Tidak --> H["Buka tab Market Basket"]
    H --> I["Pilih pasangan produk<br/>dengan lift tertinggi"]
    I --> J["Buat paket bundling<br/>atau dekatkan posisi produk"]
    J --> K{"Masih ada yang<br/>ingin ditanyakan?"}
    K -- Ya --> L["Tanya Chat AI"]
    L --> M["Baca saran AI, lalu<br/>cocokkan dengan tabel"]
    M --> K
    K -- Tidak --> Z(("Selesai"))
```

### B. Apa yang terjadi saat pengguna bertanya ke Chat AI

```mermaid
sequenceDiagram
    actor U as Pengguna
    participant D as Dashboard
    participant S as Server
    participant AI as Model AI
    U->>D: Ketik pertanyaan, misalnya "Berapa unit lunch bag yang harus dipesan?"
    D->>S: Kirim pertanyaan
    S->>S: Tambahkan ringkasan stok, 8 produk paling mendesak,<br/>dan data produk yang disebut di pertanyaan
    S->>AI: Pertanyaan + data stok
    AI-->>S: Saran singkat dengan angka (2–5 kalimat)
    S-->>D: Teruskan jawaban
    D-->>U: Tampilkan jawaban di jendela chat
```

### C. Memperbarui data dengan transaksi baru

```mermaid
flowchart TD
    S(("Mulai")) --> A["Siapkan file transaksi terbaru<br/>dengan kolom yang sama"]
    A --> B["Simpan di folder data/"]
    B --> C["Jalankan pipeline<br/>python -m src.controllers.orchestrator"]
    C --> D["Sistem menghitung ulang stok,<br/>prediksi, rekomendasi, dan market basket"]
    D --> E["Buka dashboard,<br/>klik Refresh"]
    E --> F{"Label status<br/>'Terbaru'?"}
    F -- Ya --> Z(("Selesai"))
    F -- Tidak --> C
```

> Jika prediksi berumur lebih dari 24 jam, dashboard tetap menampilkan data tetapi label status berubah menjadi **"Perlu diperbarui"**.

---

## 🧑‍💼 Panduan Pengguna

Panduan ini untuk manajer toko atau staf gudang yang memakai dashboard.

### 1. Cek kondisi stok (tab Stok & Prediksi)
1. Buka dashboard. Tab **Stok & Prediksi** terbuka otomatis.
2. Baca **kartu ringkasan** di atas:
   - **Perlu dipesan**: jumlah produk yang stoknya sudah di bawah titik pesan ulang.
   - **Risiko kehabisan**: produk yang akan habis sebelum kiriman berikutnya tiba.
   - **Nilai berisiko**: perkiraan penjualan (£) yang hilang jika produk berisiko tidak segera dipesan.
   - **Overstock**, **Deadstock**, dan **Penjualan hilang 30 hari**.
3. Kotak biru di bawahnya menunjukkan **akurasi prediksi**: rata-rata selisih prediksi per produk, dan seberapa lebih akurat dibanding metode rata-rata sederhana.

### 2. Tentukan produk yang harus dipesan
1. Centang **"Hanya yang perlu dipesan"**.
2. Di tabel, lihat kolom:
   - **Cukup untuk**: stok cukup untuk berapa hari lagi. Bar merah berarti akan habis sebelum kiriman tiba.
   - **Prediksi 7 hari**: perkiraan unit terjual minggu depan.
   - **Saran pesan**: jumlah unit yang disarankan untuk dipesan sekarang.
   - **Nilai berisiko**: penjualan yang bisa hilang jika produk ini tidak dipesan.
3. **Klik nama produk** untuk melihat grafik 90 hari: penjualan, stok, dan penjualan yang tidak terlayani, plus titik pesan ulang, stok pengaman, dan waktu kirim supplier.
4. Klik **Unduh daftar pesan** untuk mendapatkan file CSV berisi semua produk yang perlu dipesan, lengkap dengan jumlah dan nilai pesanannya. File ini bisa langsung dikirim ke supplier.

### 3. Tangani stok berlebih
| Kalau kamu melihat… | Lakukan |
|---|---|
| Label **Overstock** | Tunda pemesanan berikutnya |
| Label **Deadstock** | Rencanakan diskon atau bundling |
| Label **Promo** | Pertimbangkan promosi untuk mendorong penjualan |

### 4. Cari ide bundling (tab Market Basket)
1. Klik tab **Market Basket**.
2. Setiap baris berbunyi **"Jika membeli A → cenderung juga membeli B"**.
3. Baca angkanya:
   - **Invoice**: berapa kali kedua produk muncul di invoice yang sama.
   - **Support**: persentase invoice yang berisi kedua produk.
   - **Confidence**: dari pembeli A, berapa persen yang juga membeli B.
   - **Lift**: di atas 1 berarti saling terkait, di atas 2 berarti sangat kuat.
4. Pakai pasangan dengan **lift tertinggi** untuk paket bundling, rekomendasi "sering dibeli bersama" di toko online, atau penempatan produk yang berdekatan.

### 5. Tanya Chat AI
1. Klik **tombol chat** di pojok kanan bawah.
2. Ketik pertanyaan dalam bahasa Indonesia atau Inggris. Contoh:
   - *"Produk apa yang harus saya pesan hari ini, dan berapa unit?"*
   - *"Kenapa Jumbo Bag Red Retrospot berisiko?"* Sebut nama produk agar AI membaca datanya secara detail.
   - *"Produk mana yang sebaiknya didiskon?"*
3. AI menjawab singkat dengan angka dari data terbaru.

> AI hanya membaca data dari sistem. Tetap cek ulang angkanya di tabel sebelum mengambil keputusan besar.
>
> Di demo online, chat masih berjalan dalam **mode demo** (label "Mode demo (AI belum aktif)" di jendela chat), karena API key LLM perlu disiapkan terlebih dahulu.

---

## ⚠️ Keterbatasan

- **Stok masih simulasi.** Dataset hanya berisi penjualan, jadi stok, waktu kirim, dan penjualan hilang adalah hasil simulasi kebijakan pada bagian [Simulasi Stok](#-simulasi-stok). Untuk dipakai di toko sungguhan, ganti dengan data stok asli.
- **Kategori dibuat dari kata kunci** pada nama produk. Hampir semua produk sudah terkelompok, tetapi sebagian kecil bisa masuk kategori yang kurang tepat.
- **Satu toko online.** Data berasal dari satu peritel online di Inggris dengan banyak pembeli grosir, jadi polanya bisa berbeda dari toko fisik.
- **Chat AI di demo belum memakai model AI** karena API key perlu disiapkan. Lihat [Mengaktifkan Chat AI](#-mengaktifkan-chat-ai).
- **Hanya 300 produk terlaris** yang diprediksi. Jumlah ini bisa diubah lewat `TOP_N_PRODUCTS` di `.env`.

---

## 📁 Struktur Proyek

```text
retail-inventory-ai/
├── data/                  # Dataset dan hasil pipeline (tidak di-commit)
├── public/demo/           # Hasil dari data asli untuk mode demo (dibuat oleh scripts/export_demo.py)
├── scripts/               # export_demo.py
├── src/
│   ├── api/               # Server FastAPI
│   ├── config/            # Semua pengaturan (bisa diubah lewat .env)
│   ├── controllers/       # Orchestrator alur kerja
│   ├── data_pipeline/     # Membaca, membersihkan, dan membentuk data harian
│   ├── services/          # Simulasi stok, fitur, model, keputusan, market basket, konteks chat
│   ├── repositories/      # Baca/tulis file data, model, dan hasil (+ cadangan dari public/demo)
│   ├── llm_engine/        # Klien LLM dan prompt
│   └── dashboard/         # Frontend React (termasuk mode demo)
├── tests/                 # pytest + data tiruan berformat Online Retail II
├── .github/workflows/     # CI, build demo ke gh-pages, deploy ke Hugging Face
├── Dockerfile             # Server API untuk Hugging Face Spaces / Docker
├── render.yaml            # Alternatif deploy di Render
├── .env.example           # Contoh konfigurasi
├── requirements.txt       # Semua library (pipeline + API + test)
└── requirements-api.txt   # Library minimum untuk menjalankan API
```

---

## 🙏 Asal Proyek

Proyek ini dikembangkan ulang dari tugas kelompok mata kuliah AI for Business ITB oleh Bastian Natanael Sibarani, Gabriel Marcellino, Faishal, Gymnastiar Anwar, dan M. Rivaldi Mahari ([repositori asli](https://github.com/bastianns/AIforBusiness)). Riwayat commit versi awal tetap tersimpan di repositori ini.

Dataset: Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository, CC BY 4.0.
