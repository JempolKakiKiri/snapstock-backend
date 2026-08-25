# Smart Restock UMKM - API Documentation

Dokumentasi ini dibuat untuk memudahkan tim Frontend dalam mengintegrasikan aplikasi dengan backend API Smart Restock.

Base URL untuk API ini adalah URL tempat backend berjalan (misal: `http://localhost:3000` atau URL production).

---

## 1. Health Check

Endpoint ini digunakan untuk mengecek apakah server backend berjalan dengan baik.

### `GET /`

- **Description**: Root endpoint.
- **Response**: Text biasa (`Selamat datang di API Smart Restock UMKM!`)

### `GET /api/health`

- **Description**: API health check.
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Smart Restock Backend is up and running!"
  }
  ```

---

## 2. Inventory & Upload Nota

### `POST /api/notes/upload`

Endpoint ini digunakan untuk mengupload gambar nota/struk belanja. Sistem (menggunakan OCR/ML) akan membaca item yang ada di nota dan secara otomatis menambahkannya ke database barang dan mencatat transaksi masuk (`IN`).

- **Method**: `POST`
- **Content-Type**: `multipart/form-data`
- **Body Parameters**:
  - `image` (File / required): File gambar struk atau nota.

**Success Response (200 OK)**

```json
{
  "status": "success",
  "message": "Notes processed successfully",
  "data": [
    {
      "id": 1,
      "name": "Beras 5kg",
      "price": 60000,
      "current_stock": 10,
      "min_threshold": 5,
      "max_threshold": 20,
      "createdAt": "2023-10-25T10:00:00.000Z",
      "updatedAt": "2023-10-25T10:00:00.000Z",
      "receipt_qty": 2
    }
  ]
}
```

**Error Responses**

- **400 Bad Request**: Jika tidak ada file yang dikirim (field `image` kosong).
- **500 Internal Server Error**: Jika ada kesalahan dari ML Service atau server.

---

### `GET /api/inventory/recommendations`

Endpoint ini digunakan untuk mendapatkan **seluruh** rekomendasi barang yang stoknya sudah menipis (di bawah atau sama dengan `min_threshold`). API ini juga akan memprediksi sisa hari stok akan habis (`runout_days`) menggunakan ML.

- **Method**: `GET`
- **Parameters**: None

**Success Response (200 OK) - Jika ada rekomendasi**

```json
{
  "status": "success",
  "data": [
    {
      "product_id": 1,
      "name": "Beras 5kg",
      "current_stock": 3,
      "runout_days": 5,
      "recommended_restock_qty": 17
    },
    {
      "product_id": 2,
      "name": "Minyak Goreng 2L",
      "current_stock": 1,
      "runout_days": 2,
      "recommended_restock_qty": 29
    }
  ]
}
```

**Success Response (200 OK) - Jika tidak ada yang perlu direstock**

```json
{
  "status": "success",
  "message": "No products currently need restocking.",
  "data": []
}
```

---

### `GET /api/inventory/top-recommendations`

Endpoint ini digunakan untuk mendapatkan **top 5** rekomendasi barang yang paling butuh direstock, diurutkan berdasarkan `current_stock` yang paling sedikit.

- **Method**: `GET`
- **Parameters**: None

**Success Response (200 OK)**
Format response sama persis dengan endpoint `/api/inventory/recommendations`, hanya saja datanya dilimit maksimal 5 barang.

```json
{
  "status": "success",
  "data": [
    {
      "product_id": 1,
      "name": "Beras 5kg",
      "current_stock": 3,
      "runout_days": 5,
      "recommended_restock_qty": 17
    }
  ]
}
```

## Catatan untuk Frontend

1. **Upload File**: Pastikan ketika memanggil endpoint `/api/notes/upload`, menggunakan `FormData` agar browser secara otomatis menset `Content-Type: multipart/form-data`.
2. **CORS**: Backend sudah mengaktifkan CORS secara global, sehingga Anda bisa langsung `fetch` atau `axios` dari port Frontend (misalnya `localhost:5173` atau `localhost:3000`) ke Backend.
