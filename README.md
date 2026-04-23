# AIforBusiness - Retail Inventory Optimization

Proyek ini bertujuan untuk mentransformasi operasional ritel menggunakan AI (Predictive Models & LLM) untuk mengatasi inefisiensi supply chain seperti *overstock* dan *stockout*.

## 🏗️ Arsitektur Sistem (SLR Pattern)

Branch `bastian` menggunakan pola arsitektur **Service-Layer-Repository (SLR)** untuk memastikan kode scalable, modular, dan mudah diuji.

### Struktur Folder
```text
src/
├── config/             # Konfigurasi sentral (path, konstanta)
├── controllers/        # Orchestrator (Mengatur alur kerja antar service)
├── repositories/       # Data Access Layer (Data Access Layer)
├── services/           # Business Logic Layer (Feature Eng, ML, Simulation)
├── api/                # (Workload D) API Endpoints
├── dashboard/          # (Workload E) React/TypeScript UI
└── llm_engine/         # (Workload C) LLM Recommendations
```

## 🛡️ Status Audit & Validasi (Skor: 9/9 PRIMA)

Dataset hasil Workload A & B telah melewati audit ketat dan dinyatakan **PRIMA** dengan perbaikan pada:
- **Accuracy**: Rolling window berbasis waktu (`7D`) untuk data *sparse*.
- **Robustness**: Simulasi stok dengan *lead-time aware* dan pencatatan *lost sales*.
- **Signal Quality**: Penghilangan *noise* pada tren dan implementasi *Smart Risk Flags*.

### Smart Risk Logic
Sistem kini menggunakan logika bisnis yang lebih cerdas untuk mengurangi *false alert*:
- **Stockout Risk**: `coverage < lead_time_days`
- **Overstock Risk**: `coverage > 30` DAN tren `DECREASING`
- **Deadstock Risk**: `coverage > 30` DAN penjualan historis `< 0.1/hari`
- **Lost Sales Tracking**: Mendeteksi permintaan yang tidak terpenuhi untuk input LLM yang lebih akurat.

## 🚀 Cara Menjalankan

1. **Install Dependencies**:
   ```bash
   pip install pandas numpy xgboost holidays matplotlib
   ```

2. **Run Pipeline & Audit**:
   ```bash
   # Jalankan Pipeline Utama
   $env:PYTHONPATH = "."; python src/controllers/orchestrator.py
   
   # Jalankan Validasi EDA (Hasil di notebooks/eda_output/)
   python notebooks/eda_pipeline_validation.py
   ```

## 📋 Progress Workload (Update April 2026)
- [x] **Workload A (Data Engineering)**: Selesai & Diaudit (Skor 9/9).
- [x] **Workload B (Predictive Modeling)**: Selesai & Diaudit (Skor 9/9).
- [ ] **Workload C (LLM Engine)**: Tahap Pengembangan (Drafting Prompts).
- [ ] **Workload D (API)**: Tahap Pengembangan.
- [ ] **Workload E (Dashboard)**: Tahap Pengembangan.

---
**Kontributor Branch `bastian`**: Bastian Natanael Sibarani
