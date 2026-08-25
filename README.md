# Snapstock Backend & ML Integration

Aplikasi ini menggabungkan Node.js (Express) sebagai _backend_ utama dengan _script_ Python lokal (StatsForecast) untuk memprediksi hari kehabisan stok barang secara akurat menggunakan model TSB.

## Persyaratan Sistem

Sebelum memulai, pastikan laptopmu sudah ter-install:

1. **Node.js** (v18 atau lebih baru)
2. **PNPM versi 11.13.0** (Package Manager: `npm install -g pnpm@11.13.0`)
3. **Python 3.9+** (untuk menjalankan model Machine Learning)
4. **MySQL** (Server database harus menyala)

---

## Cara Instalasi & Menjalankan (Local)

### 1. Clone Repository & Setup Environtment

```bash
git clone <https://github.com/JempolKakiKiri/snapstock-backend.git>
cd snaptock-backend
```

```
touch .env
```

Isi file `.env` dengan konfigurasi _database_ ini:

```env
PORT=3000
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=snapstock_db
ML_PARSER_URL=http://localhost:8001/parse-notes
```

Download file **`models.zip`** dari Link Google Drive Berikut

```
https://drive.google.com/file/d/1KlS04EvprMVF0QOvGFpY4N8XkM2Xx_Yb/view?usp=sharing
```

Ekstrak file tersebut, lalu pindahkan folder `models` ke dalam direktori `ocr-service/`. (Pastikan strukturnya menjadi `ocr-service/models/rec/`).

### 2. Setup Database & Backend Utama (Node.js)

Pastikan kamu sudah menyalakan MySQL (XAMPP/Laragon) dan membuat database kosong bernama `snapstock_db`.

```bash
# Install semua dependensi Node.js
pnpm install

# (Opsional) Buat data transaksi sintetis agar AI punya data analisis
node src/seeders/transactionSeeder.js
```

### 3. Setup ML Service (Python - Prediksi TSB)

Karena Node.js akan mengeksekusi Python secara otomatis di latar belakang, buat _Virtual Environment_ (venv) khusus di folder `ml/scripts`.

**Mac/Linux:**

```bash
cd ml/scripts
python3 -m venv venv
source venv/bin/activate
pip install pandas joblib statsforecast
cd ../..
```

**Windows (PowerShell):**

```powershell
cd ml\scripts
python -m venv venv
.\venv\Scripts\activate
pip install pandas joblib statsforecast
cd ..\..
```

### 4. Setup Layanan OCR (Python - PaddleOCR)

Agar fitur upload nota berfungsi, kita perlu menjalankan server OCR di terminal terpisah.

**Mac/Linux:**

```bash
cd ocr-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install paddlepaddle==3.0.0 paddleocr==3.7.0
python3 -m uvicorn app:app --host 0.0.0.0 --port 8001
```

**Windows (PowerShell):**

```powershell
cd ocr-service
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install paddlepaddle==3.0.0 paddleocr==3.7.0
python -m uvicorn app:app --host 0.0.0.0 --port 8001
```

### 5. Jalankan Aplikasi!

Buka terminal **baru** (biarkan terminal OCR tetap jalan), arahkan ke folder utama project (sejajar `package.json`), lalu jalankan:

```bash
pnpm run dev
```

Aplikasi siap diakses! Buka tautan `http://localhost:3000` untuk mengaktifkan layanan server Snaptock !

---
