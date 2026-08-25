# Snapstock Backend & ML Integration

Aplikasi ini menggabungkan Node.js (Express) sebagai _backend_ utama dengan _script_ Python lokal (StatsForecast) untuk memprediksi hari kehabisan stok barang secara akurat menggunakan model TSB.

## Persyaratan Sistem

Sebelum memulai, pastikan laptopmu sudah ter-install:

1. **Node.js** (v18 atau lebih baru)
2. **PNPM atau NPM** (Package Manager: `npm install -g pnpm`)
3. **Python 3.9+** (untuk menjalankan model Machine Learning)
4. **MySQL** (Server database harus menyala)

---

## Cara Instalasi & Menjalankan (Local)

### 1. Setup Backend (Node.js)

Buka terminal di _root_ folder proyek ini, lalu jalankan:

```bash
# Install semua dependensi Node.js
pnpm install atau npm install

# Buat file .env (kamu bisa copy dari .env.example jika ada)
touch .env
```

Isi file `.env` dengan konfigurasi _database_ lokalmu:

```env
PORT=3000
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=snapstock_db
ML_PARSER_URL=http://localhost:8001/parse-notes
```

### 2. Setup Database & Data Sintetis

Pastikan kamu sudah membuat _database_ kosong bernama `snapstock_db` di MySQL (lewat phpMyAdmin atau DBeaver).
Setelah itu, buat data transaksi sintetis (dummy) agar model AI punya data untuk dianalisis:

```bash
node src/seeders/transactionSeeder.js
```

_(Perintah ini juga akan otomatis membuatkan tabel-tabel yang dibutuhkan)._

### 3. Setup Python Virtual Environment (Untuk Prediksi TSB)

Karena _backend_ akan mengeksekusi Python secara otomatis di latar belakang, kita wajib membuat _Virtual Environment_ (venv) tepat di folder `ml/scripts`.

**Untuk Mac/Linux:**

```bash
cd ml/scripts
python3 -m venv venv
source venv/bin/activate
pip install statsforecast pandas numpy joblib
cd ../..
```

**Untuk Windows:**

```bash
cd ml\scripts
python -m venv venv
venv\Scripts\activate
pip install statsforecast pandas numpy joblib
cd ..\..
```

### 4. Menjalankan Layanan OCR

Agar fitur _upload_ nota berfungsi, layanan OCR (FastAPI) harus menyala di terminal terpisah.

Model hasil _fine-tuning_ **tidak disimpan di repositori ini** (114 MB, melebihi batas file GitHub). Model diunduh otomatis dari [`nafisN14/snaptock`](https://huggingface.co/nafisN14/snaptock) saat layanan pertama kali dijalankan — tidak ada file yang perlu diunduh manual.

```bash
cd ocr-service
docker compose up --build
```

Tanpa Docker (Python 3.10+):

```bash
cd ocr-service
pip install -r requirements.txt
pip install paddlepaddle==3.0.0 paddleocr==3.7.0
uvicorn app:app --host 0.0.0.0 --port 8001
```

Jalankan pertama kali akan mengunduh bobot model (114 MB) lalu memuatnya, jadi tunggu sekitar 2 menit sebelum request pertama — cek kesiapan lewat `GET /health`. Untuk membangun backend tanpa menunggu model, jalankan `MOCK=1 docker compose up`: responsnya memakai _fixture_ dengan skema yang persis sama.

### 5. Jalankan Aplikasi!

Di terminal utama (di luar folder `ocr-service` dan `ml`), jalankan peladen Node.js:

```bash
pnpm run dev atau npm run dev
```

Aplikasi siap diakses! Buka browsermu di `http://localhost:3000` untuk mencoba antarmukanya.

---

## Fitur Prediksi Restock

Saat tombol **"Prediksi Restock Terkritis"** ditekan di UI:

1. Node.js akan mencari 5 barang yang sisa stoknya paling kritis (di bawah _min_threshold_).
2. Menarik riwayat penjualan mereka selama 30 hari terakhir.
3. Node.js memanggil _script_ `ml/scripts/inference_tsb.py` secara _background_ menggunakan `child_process`.
4. Python mengolah data dan mengembalikan hari prediksi kapan stok barang habis (`runout_days`).
