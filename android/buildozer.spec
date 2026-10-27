[app]

# Nama aplikasi yang tampil di Android.
title = Penghapus Metadata Video

# Nama paket & domain -> package id: org.khoziru.metadatacleaner
package.name = metadatacleaner
package.domain = org.khoziru

# Folder kode sumber (berisi main.py).
source.dir = .

# Ekstensi file yang dimasukkan ke dalam APK.
source.include_exts = py,png,jpg,kv,atlas

# Versi aplikasi.
version = 1.0

# Dependensi Python. Logika pembersih murni Python jadi cukup python3 + kivy.
requirements = python3,kivy

# Orientasi layar.
orientation = portrait

# Layar penuh (0 = ada status bar).
fullscreen = 0

# ---- Izin Android ----
# Dibutuhkan untuk membaca & menulis file video di penyimpanan.
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_VIDEO

# API target & minimum.
android.api = 34
android.minapi = 24

# Arsitektur yang di-build (hp modern = arm64-v8a; tambah armeabi-v7a bila perlu).
android.archs = arm64-v8a

# Terima lisensi SDK otomatis agar build non-interaktif.
android.accept_sdk_license = True

# Backend grafis.
# (default p4a sudah menangani SDL2 untuk Kivy)

[buildozer]

# Level log: 2 = verbose (berguna saat build pertama).
log_level = 2

# Peringatkan bila dijalankan sebagai root.
warn_on_root = 1
