"""
main.py
-------
Versi Android (Kivy) dari Penghapus Metadata Video.

Menggunakan kembali logika pembersih Python murni:
  - mp4_cleaner.py  (MP4/MOV/M4V)
  - webm_cleaner.py (WEBM/MKV)

Fitur:
  - Pilih file video lewat file chooser bawaan Kivy.
  - "Lihat Metadata": menampilkan metadata saat ini.
  - "Bersihkan Metadata": membuat <nama>_clean.<ext> dan menampilkan
    perbandingan metadata SEBELUM vs SESUDAH.

Catatan Android:
  - Butuh izin penyimpanan (diminta saat runtime pada Android 6+).
  - File hasil ditulis di folder yang dapat diakses aplikasi; jika menulis
    di samping file asli gagal (izin), fallback ke storage privat aplikasi.
"""

import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

import mp4_cleaner
import webm_cleaner

MP4_EXTS = {".mp4", ".mov", ".m4v", ".m4a"}
WEBM_EXTS = {".webm", ".mkv"}

# ---- Deteksi Android (opsional; aman dijalankan di desktop untuk uji UI) ----
try:
    from android.permissions import request_permissions, Permission  # type: ignore
    from android.storage import primary_external_storage_path  # type: ignore
    ANDROID = True
except ImportError:
    ANDROID = False


def read_metadata(input_path):
    """Baca metadata (nama, nilai) sesuai ekstensi. [] bila tak didukung."""
    ext = os.path.splitext(input_path)[1].lower()
    try:
        if ext in MP4_EXTS:
            return mp4_cleaner.read_metadata(input_path)
        if ext in WEBM_EXTS:
            return webm_cleaner.read_metadata(input_path)
    except Exception:  # noqa: BLE001
        return []
    return []


def format_metadata(pairs):
    if not pairs:
        return "(tidak ada metadata deskriptif)"
    return "\n".join(f"  - {name}: {value}" for name, value in pairs)


def make_output_path(input_path):
    """Path keluaran <nama>_clean.<ext>, dengan fallback ke storage privat."""
    base, ext = os.path.splitext(input_path)
    candidate = f"{base}_clean{ext}"
    # Uji apakah folder sumber bisa ditulisi; jika tidak, pakai app storage.
    folder = os.path.dirname(candidate) or "."
    if os.access(folder, os.W_OK):
        return candidate
    app = App.get_running_app()
    out_dir = getattr(app, "user_data_dir", folder)
    name = os.path.basename(candidate)
    return os.path.join(out_dir, name)


def process_file(input_path):
    """Bersihkan satu file. Return (output_path, pesan, meta_before, meta_after)."""
    output_path = make_output_path(input_path)
    ext = os.path.splitext(input_path)[1].lower()
    meta_before = read_metadata(input_path)

    if ext in MP4_EXTS:
        info = mp4_cleaner.clean_mp4(input_path, output_path)
        meta_after = read_metadata(output_path)
        return (output_path, f"{info['removed']} atom metadata dihapus",
                meta_before, meta_after)

    if ext in WEBM_EXTS:
        info = webm_cleaner.clean_webm(input_path, output_path)
        n = len(info["removed"])
        meta_after = read_metadata(output_path)
        return (output_path, f"{n} elemen metadata dihapus",
                meta_before, meta_after)

    raise ValueError(
        f"Format '{ext}' belum didukung. Gunakan MP4/MOV/M4V/WEBM/MKV."
    )


class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=6, padding=8, **kwargs)
        self.selected = None

        self.add_widget(Label(
            text="[b]Penghapus Metadata Video[/b]", markup=True,
            size_hint_y=None, height="36dp"))

        start_dir = self._default_dir()
        self.chooser = FileChooserListView(
            path=start_dir,
            filters=["*.mp4", "*.mov", "*.m4v", "*.m4a", "*.webm", "*.mkv"],
        )
        self.chooser.bind(selection=self._on_select)
        self.add_widget(self.chooser)

        self.status = Label(
            text="Pilih file video di atas.", size_hint_y=None, height="30dp")
        self.add_widget(self.status)

        btn_row = BoxLayout(size_hint_y=None, height="52dp", spacing=6)
        self.view_btn = Button(text="Lihat Metadata", on_release=self.on_view)
        self.clean_btn = Button(
            text="Bersihkan Metadata", background_color=(0.15, 0.4, 0.9, 1),
            on_release=self.on_clean)
        btn_row.add_widget(self.view_btn)
        btn_row.add_widget(self.clean_btn)
        self.add_widget(btn_row)

    def _default_dir(self):
        if ANDROID:
            try:
                return primary_external_storage_path()
            except Exception:  # noqa: BLE001
                pass
        return os.path.expanduser("~")

    def _on_select(self, _chooser, selection):
        if selection:
            self.selected = selection[0]
            self.status.text = f"Dipilih: {os.path.basename(self.selected)}"

    def _require_selection(self):
        if not self.selected or not os.path.isfile(self.selected):
            self._popup("Info", "Pilih satu file video terlebih dahulu.")
            return False
        return True

    def on_view(self, *_):
        if not self._require_selection():
            return
        pairs = read_metadata(self.selected)
        name = os.path.basename(self.selected)
        self._popup("Metadata Saat Ini",
                    f"=== {name} ===\n{format_metadata(pairs)}")

    def on_clean(self, *_):
        if not self._require_selection():
            return
        self.status.text = "Memproses..."
        # Jalankan setelah frame berikutnya agar label status ter-update dulu.
        Clock.schedule_once(lambda _dt: self._do_clean(), 0.05)

    def _do_clean(self):
        name = os.path.basename(self.selected)
        try:
            out, msg, before, after = process_file(self.selected)
            self.status.text = f"Selesai: {msg}"
            report = (
                f"=== {name} ===\n{msg}\n\n"
                f"SEBELUM:\n{format_metadata(before)}\n\n"
                f"SESUDAH:\n{format_metadata(after)}\n\n"
                f"File hasil:\n{out}"
            )
            self._popup("Metadata Sebelum & Sesudah", report)
            # Segarkan daftar file agar file _clean muncul.
            self.chooser._update_files()
        except Exception as e:  # noqa: BLE001
            self.status.text = "Gagal."
            self._popup("Gagal", f"{name}:\n{e}")

    def _popup(self, title, text):
        content = ScrollView()
        lbl = Label(text=text, size_hint_y=None, halign="left", valign="top")
        lbl.bind(width=lambda s, w: s.setter("text_size")(s, (w, None)))
        lbl.bind(texture_size=lambda s, ts: s.setter("height")(s, ts[1]))
        content.add_widget(lbl)
        Popup(title=title, content=content, size_hint=(0.95, 0.9)).open()


class VideoMetadataApp(App):
    title = "Penghapus Metadata Video"

    def build(self):
        if ANDROID:
            try:
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ])
            except Exception:  # noqa: BLE001
                pass
        return RootLayout()


if __name__ == "__main__":
    VideoMetadataApp().run()
