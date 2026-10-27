# Penghapus Metadata Video — Versi Android (APK)

Versi Android dari aplikasi, dibuat dengan **Kivy** dan di-build menjadi APK
menggunakan **Buildozer**. Logika pembersih memakai kembali modul Python murni
`mp4_cleaner.py` dan `webm_cleaner.py` (tanpa dependensi eksternal, tanpa ffmpeg).

## Isi Folder
```
android/
├── main.py           # UI Kivy (pilih file, lihat metadata, bersihkan, sebelum/sesudah)
├── mp4_cleaner.py    # Inti pembersih MP4/MOV (sama dengan versi desktop)
├── webm_cleaner.py   # Inti pembersih WEBM/MKV
├── buildozer.spec    # Konfigurasi build APK
└── README.md         # File ini
```

## Penting: Build APK HANYA bisa di Linux
Buildozer tidak berjalan di Windows murni. Pilih salah satu:
- **WSL2** (Ubuntu) di Windows — paling praktis.
- **Linux** asli / VM.
- **Docker** (image resmi `kivy/buildozer`).

Build pertama mengunduh Android SDK/NDK (beberapa GB) dan bisa makan waktu
15–40 menit. Build berikutnya jauh lebih cepat.

---

## Opsi A — WSL2 / Ubuntu

1. Install WSL (di PowerShell Windows, sekali saja):
   ```powershell
   wsl --install -d Ubuntu
   ```
   Buka ulang, buat user Ubuntu.

2. Di terminal Ubuntu, pasang prasyarat:
   ```bash
   sudo apt update
   sudo apt install -y python3-pip git zip unzip openjdk-17-jdk \
       autoconf libtool pkg-config zlib1g-dev libncurses-dev \
       libffi-dev libssl-dev build-essential ccache
   pip3 install --user buildozer cython
   export PATH="$HOME/.local/bin:$PATH"
   ```

3. Salin folder `android/` ke dalam WSL (hindari membangun langsung dari
   `/mnt/c` karena izin file lambat/bermasalah):
   ```bash
   cp -r /mnt/c/Users/Khoziru/video-metadata-cleaner/android ~/metadata-cleaner
   cd ~/metadata-cleaner
   ```

4. Build APK debug:
   ```bash
   buildozer -v android debug
   ```
   Hasil: `bin/metadatacleaner-1.0-arm64-v8a-debug.apk`

5. Salin APK kembali ke Windows:
   ```bash
   cp bin/*.apk /mnt/c/Users/Khoziru/Downloads/
   ```

---

## Opsi B — Docker (tanpa pasang toolchain manual)

Dari dalam folder `android/`:
```bash
docker run --rm -it -v "$PWD":/home/user/hostcwd kivy/buildozer \
    -v android debug
```
APK muncul di `android/bin/`. (Di Windows, jalankan perintah ini dari
Git Bash/WSL agar `$PWD` benar, atau ganti dengan path absolut.)

---

## Memasang APK ke HP
1. Aktifkan **Opsi Pengembang** → **USB Debugging**, atau izinkan
   **Instal dari sumber tak dikenal**.
2. Via kabel + ADB:
   ```bash
   adb install bin/metadatacleaner-1.0-arm64-v8a-debug.apk
   ```
   Atau salin file `.apk` ke HP dan buka untuk memasang.

---

## Cara Pakai di HP
1. Buka aplikasi **Penghapus Metadata Video**.
2. Izinkan akses penyimpanan saat diminta.
3. Telusuri dan pilih file video (MP4/MOV/M4V/WEBM/MKV).
4. **Lihat Metadata** untuk melihat metadata saat ini, atau
   **Bersihkan Metadata** untuk membuat `<nama>_clean.<ext>`.
5. Muncul laporan **SEBELUM vs SESUDAH**. Lokasi file hasil ditampilkan
   di akhir laporan.

> Catatan izin: pada Android modern (scoped storage), jika menulis di samping
> file asli ditolak, aplikasi otomatis menyimpan hasil ke folder privat
> aplikasi dan menampilkan path-nya di laporan.

---

## Format Didukung (tanpa ffmpeg)
| Format            | Baca metadata | Bersihkan |
|-------------------|:-------------:|:---------:|
| MP4, MOV, M4V     | ✅            | ✅        |
| WEBM, MKV         | ✅            | ✅        |
| Lainnya (AVI dll) | ❌            | ❌        |

Stream video/audio tidak di-encode ulang, jadi kualitas tetap dan prosesnya cepat.

---

## Menguji Logika Inti di Desktop (opsional)
Logika pembersih bisa diuji tanpa Android/Kivy:
```bash
cd android
python -c "import mp4_cleaner; print(mp4_cleaner.read_metadata('contoh.mp4'))"
```

## Rilis APK (opsional)
APK debug sudah bisa dipasang. Untuk APK rilis bertanda tangan:
```bash
buildozer android release
```
Lalu tandatangani dengan `apksigner`/`jarsigner` memakai keystore Anda.
