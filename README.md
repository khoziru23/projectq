# Penghapus Metadata Video

[![Build APK](https://github.com/khoziru23/projectq/actions/workflows/build-apk.yml/badge.svg)](https://github.com/khoziru23/projectq/actions/workflows/build-apk.yml)

Aplikasi GUI sederhana untuk menghapus metadata dari file video.
Dibuat dengan Python (tkinter) — **tanpa perlu instalasi library tambahan**.

## Fitur
- Antarmuka grafis sederhana: pilih file, klik, selesai.
- Pembersih **MP4 / MOV** murni Python (tanpa ffmpeg). Menghapus atom metadata
  `udta` dan `meta` (judul, author, perangkat, GPS/lokasi, tag iTunes, dsb).
- **Opsional**: jika `ffmpeg` terpasang, mendukung banyak format lain
  (MKV, AVI, WEBM, FLV, WMV) dengan menyalin stream tanpa metadata.
- File asli **tidak diubah**. Hasil disimpan sebagai `namafile_clean.ext`.

## Persyaratan
- Python 3.8+ (diuji pada Python 3.14). tkinter sudah termasuk bawaan Python di Windows.
- (Opsional) `ffmpeg` di PATH untuk format selain MP4/MOV.

## Cara Menjalankan (GUI)
```bash
cd video-metadata-cleaner
python app.py
```
Langkah:
1. Klik **Tambah File...** lalu pilih satu atau beberapa video.
2. (Opsional) centang **Gunakan ffmpeg** jika tersedia untuk format non-MP4.
3. Klik **Bersihkan Metadata**.
4. File hasil muncul di folder yang sama dengan akhiran `_clean`.

## Cara Menjalankan (baris perintah)
Membersihkan satu file MP4/MOV tanpa GUI:
```bash
python mp4_cleaner.py input.mp4 output.mp4
```

## Menjalankan Pengujian
```bash
python test_cleaner.py
```
Membuat MP4 sintetis berisi metadata, membersihkannya, dan memverifikasi
metadata hilang sementara struktur video tetap utuh.

## Format Didukung
| Format            | Tanpa ffmpeg | Dengan ffmpeg |
|-------------------|:------------:|:-------------:|
| MP4, MOV, M4V     | ✅           | ✅            |
| MKV, AVI, WEBM... | ❌           | ✅            |

## Cara Memasang ffmpeg (opsional, Windows)
- Unduh dari https://ffmpeg.org/download.html, atau
- `winget install ffmpeg`, lalu buka ulang terminal.

## Catatan
- Pembersih Python menghapus metadata level-kontainer (`udta`/`meta`).
  Thumbnail dan tag yang tersimpan di sana akan ikut terhapus.
- Stream video/audio tidak di-encode ulang, jadi kualitas tidak berubah dan prosesnya cepat.

## Struktur Berkas
```
video-metadata-cleaner/
├── app.py            # Aplikasi GUI
├── mp4_cleaner.py    # Inti pembersih MP4/MOV (Python murni)
├── test_cleaner.py   # Pengujian otomatis
└── README.md
```
