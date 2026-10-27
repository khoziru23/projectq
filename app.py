"""
app.py
------
Aplikasi GUI sederhana untuk MENGHAPUS METADATA VIDEO.

Fitur:
- Pilih satu atau beberapa file video.
- Metode 1 (default, tanpa instalasi): pembersih MP4/MOV murni Python.
- Metode 2 (opsional): ffmpeg, jika terpasang, mendukung banyak format
  (mkv, avi, webm, dll) dengan menyalin stream tanpa metadata.
- Hasil disimpan sebagai file baru "<nama>_clean.<ext>" (file asli tidak diubah).

Jalankan:  python app.py
"""

import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mp4_cleaner
import webm_cleaner

MP4_EXTS = {".mp4", ".mov", ".m4v", ".m4a"}
WEBM_EXTS = {".webm", ".mkv"}


def ffmpeg_path():
    """Kembalikan path ffmpeg bila tersedia di PATH, selain itu None."""
    return shutil.which("ffmpeg")


def clean_with_ffmpeg(input_path, output_path):
    """Hapus metadata menggunakan ffmpeg (copy stream, buang semua metadata)."""
    cmd = [
        ffmpeg_path(),
        "-y",
        "-i", input_path,
        "-map_metadata", "-1",   # buang metadata global
        "-map_chapters", "-1",   # buang chapter
        "-c", "copy",            # salin stream tanpa re-encode (cepat)
        output_path,
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace")[-500:])


def make_output_path(input_path):
    base, ext = os.path.splitext(input_path)
    return f"{base}_clean{ext}"


def read_metadata(input_path):
    """
    Baca metadata deskriptif dari file, memilih cleaner sesuai ekstensi.
    Return list pasangan (nama, nilai). List kosong jika tidak ada metadata
    atau format tidak didukung pembacaan tanpa ffmpeg.
    """
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
    """Ubah list (nama, nilai) menjadi teks yang mudah dibaca."""
    if not pairs:
        return "(tidak ada metadata deskriptif)"
    return "\n".join(f"  • {name}: {value}" for name, value in pairs)


def process_file(input_path, use_ffmpeg):
    """Proses satu file. Kembalikan (output_path, pesan, meta_before, meta_after)."""
    output_path = make_output_path(input_path)
    ext = os.path.splitext(input_path)[1].lower()

    meta_before = read_metadata(input_path)

    if use_ffmpeg and ffmpeg_path():
        clean_with_ffmpeg(input_path, output_path)
        meta_after = read_metadata(output_path)
        return output_path, "dibersihkan dengan ffmpeg", meta_before, meta_after

    if ext in MP4_EXTS:
        info = mp4_cleaner.clean_mp4(input_path, output_path)
        meta_after = read_metadata(output_path)
        return (output_path, f"{info['removed']} atom metadata dihapus (Python)",
                meta_before, meta_after)

    if ext in WEBM_EXTS:
        info = webm_cleaner.clean_webm(input_path, output_path)
        n = len(info["removed"])
        meta_after = read_metadata(output_path)
        return (output_path,
                f"{n} elemen metadata dihapus (Python): {', '.join(info['removed'])}",
                meta_before, meta_after)

    # Format lain tanpa ffmpeg -> tidak bisa diproses.
    raise ValueError(
        f"Format '{ext}' butuh ffmpeg. Pasang ffmpeg atau gunakan file MP4/MOV/WEBM/MKV."
    )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Penghapus Metadata Video")
        self.geometry("620x460")
        self.minsize(520, 400)
        self.files = []
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        header = tk.Label(
            self, text="Penghapus Metadata Video",
            font=("Segoe UI", 15, "bold"),
        )
        header.pack(**pad)

        info = "Pilih file video, lalu klik 'Bersihkan'. File hasil disimpan sebagai *_clean."
        tk.Label(self, text=info, fg="#555").pack(padx=10)

        # Status ffmpeg
        if ffmpeg_path():
            ff_text = "ffmpeg: TERDETEKSI (mendukung semua format)"
            ff_color = "#1a7f37"
        else:
            ff_text = "ffmpeg: tidak ada (didukung: MP4/MOV/WEBM/MKV)"
            ff_color = "#b35900"
        tk.Label(self, text=ff_text, fg=ff_color, font=("Segoe UI", 9)).pack(padx=10)

        # Daftar file
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=8)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        self.listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        # Tombol file
        btns = tk.Frame(self)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="Tambah File...", command=self.add_files).pack(side="left")
        tk.Button(btns, text="Lihat Metadata", command=self.view_metadata).pack(side="left", padx=6)
        tk.Button(btns, text="Hapus Terpilih", command=self.remove_selected).pack(side="left", padx=6)
        tk.Button(btns, text="Kosongkan", command=self.clear_files).pack(side="left")

        # Opsi ffmpeg
        self.use_ffmpeg_var = tk.BooleanVar(value=bool(ffmpeg_path()))
        self.chk = tk.Checkbutton(
            self, text="Gunakan ffmpeg bila tersedia (dukung lebih banyak format)",
            variable=self.use_ffmpeg_var,
            state="normal" if ffmpeg_path() else "disabled",
        )
        self.chk.pack(anchor="w", padx=10)

        # Progress + status
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(8, 2))
        self.status = tk.Label(self, text="Siap.", anchor="w", fg="#333")
        self.status.pack(fill="x", padx=10)

        # Tombol aksi
        self.run_btn = tk.Button(
            self, text="Bersihkan Metadata", command=self.run,
            bg="#2563eb", fg="white", font=("Segoe UI", 11, "bold"),
            activebackground="#1d4ed8", activeforeground="white",
        )
        self.run_btn.pack(fill="x", padx=10, pady=10)

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Pilih file video",
            filetypes=[
                ("Video", "*.mp4 *.mov *.m4v *.mkv *.avi *.webm *.flv *.wmv"),
                ("Semua file", "*.*"),
            ],
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert("end", p)

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            del self.files[i]
            self.listbox.delete(i)

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(0, "end")

    def view_metadata(self):
        """Tampilkan metadata file yang dipilih (atau semua jika tidak ada pilihan)."""
        sel = self.listbox.curselection()
        targets = [self.files[i] for i in sel] if sel else list(self.files)
        if not targets:
            messagebox.showinfo("Info", "Tambahkan dan/atau pilih file dulu.")
            return
        parts = []
        for path in targets:
            name = os.path.basename(path)
            pairs = read_metadata(path)
            parts.append(f"=== {name} ===\n{format_metadata(pairs)}\n")
        self._show_report("Metadata Saat Ini", "\n".join(parts))

    def _show_report(self, title, text):
        """Jendela teks read-only yang bisa digulir untuk menampilkan laporan."""
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("640x460")
        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        txt = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                      font=("Consolas", 10))
        txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=txt.yview)
        txt.insert("1.0", text)
        txt.config(state="disabled")
        tk.Button(win, text="Tutup", command=win.destroy).pack(pady=6)

    def run(self):
        if not self.files:
            messagebox.showinfo("Info", "Tambahkan dulu minimal satu file video.")
            return
        self.run_btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        t = threading.Thread(target=self._worker, daemon=True)
        t.start()

    def _worker(self):
        use_ffmpeg = self.use_ffmpeg_var.get()
        ok, fail = 0, 0
        errors = []
        reports = []
        for idx, path in enumerate(list(self.files), start=1):
            name = os.path.basename(path)
            self._set_status(f"Memproses ({idx}/{len(self.files)}): {name}")
            try:
                out, msg, meta_before, meta_after = process_file(path, use_ffmpeg)
                ok += 1
                reports.append(
                    f"=== {name} ===\n"
                    f"SEBELUM:\n{format_metadata(meta_before)}\n"
                    f"SESUDAH:\n{format_metadata(meta_after)}\n"
                )
            except Exception as e:  # noqa: BLE001
                fail += 1
                errors.append(f"{name}: {e}")
            self._set_progress(idx)

        summary = f"Selesai. Berhasil: {ok}, Gagal: {fail}."
        self._set_status(summary)
        self.after(0, lambda: self._done(summary, errors, reports))

    def _done(self, summary, errors, reports):
        self.run_btn.config(state="normal")
        if reports:
            self._show_report("Metadata Sebelum & Sesudah", "\n".join(reports))
        if errors:
            messagebox.showwarning("Selesai dengan sebagian gagal",
                                   summary + "\n\n" + "\n".join(errors[:10]))
        else:
            messagebox.showinfo("Selesai", summary + "\nFile hasil berakhiran _clean.")

    def _set_status(self, text):
        self.after(0, lambda: self.status.config(text=text))

    def _set_progress(self, value):
        self.after(0, lambda: self.progress.config(value=value))


if __name__ == "__main__":
    App().mainloop()
