# KosNest - Aplikasi Web Informasi & Booking Kos Modern

Aplikasi web informasi dan pemesanan kamar kos berbasis **Python Flask** dan **SQLite**, dirancang berdasarkan **Perancangan Prototipe UI Interaktif Berbasis Ergonomi** untuk persona calon penghuni (**Titut**) dan pemilik kos (**Admin**).

---

## 👥 Persona & Latar Belakang (Titut)
- **Nama**: Titut (Mahasiswi semester 3, perantau baru)
- **Tujuan**:
  1. Mengetahui **slot kamar kosong** secara langsung tanpa harus tanya pemilik kos berulang kali.
  2. Melihat **foto kos dan kamar yang jelas** sesuai kondisi asli.
  3. Membandingkan **fasilitas tiap kamar** (AC, kamar mandi dalam, kasur, WiFi, dll.) beserta harganya.
  4. **Login dan Booking** secara mudah lalu membayar lewat simulasi e-banking tanpa harus bertemu tatap muka.
  5. Memantau **riwayat pembayaran** agar bukti transfer tersimpan rapi dan status sewa jelas.

---

## 🌟 Fitur Utama Sesuai Spesifikasi

### 1. Autentikasi & Halaman Awal
- **Halaman Awal**: Rute utama (`/`) langsung mengarahkan ke halaman **Login** (`/login`).
- **Pendaftaran Akun Baru (`/register`)**: Otomatis mendapatkan peran sebagai **User (Calon Penghuni)**.
- **Tersedia Akun Bawaan (Demo Praktikum)**:
  - **Calon Penghuni (Titut)**: `titut` / `titut123`
  - **Pemilik Kos (Admin)**: `admin` / `admin123`
  *(Terdapat tombol klik instan untuk mengisi form login demo).*

### 2. Sisi Penghuni (Calon Penghuni)
- **Papan Slot Kamar**: Indikator slot realtime: *Total Kamar*, *Slot Kosong (Hijau)*, *Dipesan (Kuning)*, dan *Kamar Terisi (Merah)*.
- **Galeri Foto Kos**: Foto lingkungan & fasilitas umum kos (Tampak Depan, Dapur Bersama, Area Parkir Berkanopi, Rooftop Jemuran).
- **Filter & Pencarian**: Filter rentang harga (Min - Max), filter status kamar (semua / hanya kosong), dan kolom pencarian nama/fasilitas.
- **Detail Kamar**: Menampilkan spesifikasi luas, posisi lantai, galeri foto lengkap tiap kamar, serta daftar fasilitas spesifik per kamar.
- **Booking & E-Banking**:
  - Memilih metode bank transfer (BCA, Mandiri, BRI, BNI).
  - Menampilkan rekening resmi pemilik kos dan nominal tepat.
  - Kamar yang dipesan otomatis berstatus **DIPESAN** dan dikunci sehingga tidak dapat dipesan orang lain.
- **Unggah Bukti Transfer**:
  - Calon penghuni mengunggah struk/screenshot transfer m-banking.
  - Status berubah menjadi **"Menunggu verifikasi pemilik kos"**.
- **Riwayat Pembayaran**:
  - Memantau kode booking, tanggal, nominal, metode bank, status transaksi, bukti bayar (popup pratinjau), dan catatan alasan penolakan jika ditolak.

### 3. Sisi Pemilik Kos (Admin)
- **Dashboard Admin**:
  - Ringkasan statistik slot kamar (kosong, dipesan, terisi).
  - Notifikasi pembayaran yang perlu diverifikasi segera.
- **Kelola Kamar (CRUD)**:
  - Tambah kamar baru beserta foto utama, galeri foto tambahan, dan checklist fasilitas lengkap.
  - Ubah data kamar, harga, ukuran, fasilitas, serta status kamar.
  - Hapus data kamar.
- **Kelola Foto Kos**: Tambah dan hapus galeri foto lingkungan bersama kos.
- **Verifikasi Pembayaran**:
  - Memeriksa nama penyewa, no HP/WhatsApp, kamar, nominal, dan foto bukti transfer.
  - **Setujui**: Status booking menjadi *Disetujui (Lunas)* dan status kamar otomatis berubah menjadi **TERISI**.
  - **Tolak**: Menampilkan dialog untuk memasukkan **alasan penolakan** (misal: "Nominal tidak sesuai" atau "Struk buram"). Kamar otomatis dibuka kembali menjadi **KOSONG** atau penyewa dapat mengunggah ulang sebelum 24 jam.

### 4. Aturan Alur & Auto-Expired 24 Jam
- Kamar yang berstatus `dipesan` atau `terisi` **tidak dapat dipesan** oleh orang lain.
- Booking yang belum dibayar dalam batas waktu **24 jam** otomatis berstatus **KEDALUWARSA** dan status kamar dikembalikan menjadi **KOSONG** agar dapat dipesan kembali.
- Sistem otomatis mengecek dan memperbarui status expired pada setiap request maupun latar belakang.

---

## 📁 Struktur Direktori Proyek

```
kosnest/
├── app.py                  # Server utama Flask & rute aplikasi
├── database.py             # Koneksi SQLite, inisialisasi tabel, & logika auto-expire
├── seed_data.py            # Generator SVG placeholder & data awal demo
├── test_kosnest.py         # 7 automated unit/integration tests
├── README.md               # Dokumentasi sistem
├── static/
│   ├── css/
│   │   └── style.css       # Styling antarmuka berbasis ergonomi (Bootstrap 5)
│   ├── js/
│   │   └── main.js         # Countdown timer 24 jam, modal pratinjau gambar, dll.
│   └── uploads/
│       ├── rooms/          # Foto kamar & galeri kamar
│       ├── kos/            # Foto lingkungan kos bersama
│       └── proofs/         # Bukti transfer pembayaran
└── templates/
    ├── base.html           # Layout dasar & navigasi dinamis per-role
    ├── auth/
    │   ├── login.html      # Halaman awal login
    │   └── register.html   # Pendaftaran akun penghuni baru
    ├── user/
    │   ├── katalog.html     # Papan slot kamar, filter & galeri kos
    │   ├── detail_kamar.html# Detail kamar & rincian fasilitas
    │   ├── booking.html    # Form pemilihan bank & konfirmasi booking
    │   ├── upload_bukti.html# Petunjuk transfer & upload bukti
    │   └── riwayat.html    # Tabel riwayat pembayaran
    └── admin/
        ├── dashboard.html  # Dashboard pemilik kos
        ├── kamar_list.html # Daftar kamar kos
        ├── kamar_form.html # Form tambah / ubah kamar
        ├── galeri_kos.html # Kelola foto lingkungan kos
        └── verifikasi_list.html # Verifikasi persetujuan / penolakan
```

---

## 🚀 Cara Menjalankan Aplikasi

1. Buka terminal PowerShell / Command Prompt di folder proyek:
   ```powershell
   cd C:\Users\asuss\.gemini\antigravity\scratch\kosnest
   ```

2. Jalankan aplikasi Flask:
   ```powershell
   python app.py
   ```

3. Buka peramban (browser) dan akses:
   ```
   http://127.0.0.1:5000
   ```

4. Uji alur sistem dengan akun bawaan:
   - Masuk sebagai **Titut** (`titut` / `titut123`) untuk mencoba melihat slot kamar kosong, filter harga, melihat fasilitas, memesan kamar, dan mengunggah bukti bayar.
   - Masuk sebagai **Admin** (`admin` / `admin123`) untuk mengelola kamar, menambah foto kos, dan menyetujui/menolak verifikasi transfer.

---

## 🧪 Menjalankan Pengujian Otomatis (Unit Testing)

Jalankan test suite untuk memastikan seluruh 7 skenario alur bekerja dengan benar:
```powershell
python test_kosnest.py
```
Hasil:
```
----------------------------------------------------------------------
Ran 7 tests in 6.5s

OK
```
