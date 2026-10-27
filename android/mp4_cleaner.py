"""
mp4_cleaner.py
--------------
Pembersih metadata untuk file MP4 / MOV (ISO Base Media File Format)
menggunakan Python murni, TANPA dependensi eksternal.

Cara kerja singkat:
- File MP4/MOV tersusun dari "atom" (atau "box"). Setiap atom punya:
  [4 byte ukuran][4 byte tipe][data...]
- Metadata (judul, author, GPS, software, tags iTunes, dsb) umumnya
  tersimpan di dalam atom:  moov -> udta  (user data, termasuk 'meta').
- Dengan membuang atom 'udta' di dalam 'moov', metadata deskriptif terhapus.
  Ukuran atom induk ('moov' dan atom pembungkusnya) diperbaiki otomatis.

Catatan:
- Ini menghapus metadata level-kontainer (udta/meta). Stream video/audio
  tetap utuh sehingga file tetap dapat diputar.
"""

import struct
import os

# Tipe atom yang merupakan "kontainer" (berisi atom anak di dalamnya).
CONTAINER_ATOMS = {
    b"moov", b"trak", b"edts", b"mdia", b"minf", b"dinf", b"stbl",
    b"mvex", b"moof", b"traf", b"mfra", b"udta", b"meta", b"ilst",
}

# Atom yang akan dihapus sebagai metadata.
ATOMS_TO_REMOVE = {b"udta", b"meta"}


class Atom:
    """Representasi satu atom MP4."""

    def __init__(self, atom_type, size, header_size, data=None, children=None):
        self.type = atom_type          # bytes, 4 karakter
        self.size = size               # ukuran total atom (termasuk header)
        self.header_size = header_size # 8 atau 16 (versi 64-bit)
        self.data = data               # bytes mentah (untuk atom non-kontainer)
        self.children = children or [] # list Atom (untuk atom kontainer)

    @property
    def is_container(self):
        return self.type in CONTAINER_ATOMS


def _read_atoms(buf, start, end):
    """Baca daftar atom dari buf[start:end], rekursif untuk kontainer."""
    atoms = []
    offset = start
    while offset < end:
        if offset + 8 > end:
            # Sisa byte tidak cukup untuk header; perlakukan sebagai data mentah.
            break
        size = struct.unpack(">I", buf[offset:offset + 4])[0]
        atom_type = buf[offset + 4:offset + 8]
        header_size = 8

        if size == 1:
            # Ukuran 64-bit disimpan di 8 byte berikutnya.
            if offset + 16 > end:
                break
            size = struct.unpack(">Q", buf[offset + 8:offset + 16])[0]
            header_size = 16
        elif size == 0:
            # Ukuran 0 berarti atom memanjang sampai akhir file.
            size = end - offset

        if size < header_size or offset + size > end:
            # Atom rusak / tidak valid -> hentikan parsing di level ini.
            break

        atom_end = offset + size

        if atom_type in CONTAINER_ATOMS:
            # 'meta' punya 4 byte version/flags sebelum atom anak (full box).
            child_start = offset + header_size
            if atom_type == b"meta":
                child_start += 4
            children = _read_atoms(buf, child_start, atom_end)
            atom = Atom(atom_type, size, header_size, children=children)
            # Simpan prefiks khusus 'meta' (version/flags) bila ada.
            if atom_type == b"meta":
                atom.data = buf[offset + header_size:offset + header_size + 4]
        else:
            data = buf[offset + header_size:atom_end]
            atom = Atom(atom_type, size, header_size, data=data)

        atoms.append(atom)
        offset = atom_end
    return atoms


def _filter_atoms(atoms):
    """Buang atom metadata secara rekursif. Kembalikan (list_baru, jumlah_dihapus)."""
    result = []
    removed = 0
    for atom in atoms:
        if atom.type in ATOMS_TO_REMOVE:
            removed += 1
            continue
        if atom.is_container and atom.children:
            new_children, child_removed = _filter_atoms(atom.children)
            atom.children = new_children
            removed += child_removed
        result.append(atom)
    return result, removed


def _serialize_atom(atom):
    """Ubah Atom kembali menjadi bytes, menghitung ulang ukuran."""
    if atom.is_container:
        body = b""
        # 'meta' menulis ulang version/flags terlebih dahulu.
        if atom.type == b"meta" and atom.data is not None:
            body += atom.data
        for child in atom.children:
            body += _serialize_atom(child)
        payload = body
    else:
        payload = atom.data if atom.data is not None else b""

    total = len(payload) + 8
    # Gunakan header 8-byte selama ukuran muat dalam 32-bit.
    if total < 2**32:
        header = struct.pack(">I", total) + atom.type
        return header + payload
    else:
        # Fallback header 64-bit untuk file sangat besar.
        header = struct.pack(">I", 1) + atom.type + struct.pack(">Q", total + 8)
        return header + payload


def clean_mp4(input_path, output_path):
    """
    Baca file MP4/MOV, hapus atom metadata (udta/meta), tulis ke output_path.

    Return: dict berisi info {'removed': int, 'input_size': int, 'output_size': int}
    Raise ValueError jika file bukan MP4/MOV yang valid.
    """
    with open(input_path, "rb") as f:
        buf = f.read()

    if len(buf) < 8:
        raise ValueError("File terlalu kecil atau kosong.")

    atoms = _read_atoms(buf, 0, len(buf))
    if not atoms:
        raise ValueError("Tidak dapat mem-parsing atom. File mungkin bukan MP4/MOV valid.")

    # Validasi: harus ada atom 'ftyp' atau 'moov' sebagai tanda MP4/MOV.
    top_types = {a.type for a in atoms}
    if b"ftyp" not in top_types and b"moov" not in top_types:
        raise ValueError("Bukan file MP4/MOV (atom 'ftyp'/'moov' tidak ditemukan).")

    new_atoms, removed = _filter_atoms(atoms)

    out = b"".join(_serialize_atom(a) for a in new_atoms)

    with open(output_path, "wb") as f:
        f.write(out)

    return {
        "removed": removed,
        "input_size": len(buf),
        "output_size": len(out),
    }


def list_metadata_atoms(input_path):
    """Kembalikan daftar path atom metadata yang ditemukan (untuk inspeksi)."""
    with open(input_path, "rb") as f:
        buf = f.read()
    atoms = _read_atoms(buf, 0, len(buf))
    found = []

    def walk(atom_list, prefix=""):
        for a in atom_list:
            name = prefix + a.type.decode("latin-1", "replace")
            if a.type in ATOMS_TO_REMOVE:
                found.append(name)
            if a.is_container:
                walk(a.children, name + "/")

    walk(atoms)
    return found


# Nama ramah untuk tag MP4/QuickTime umum (prefiks 0xA9 = '©').
_MP4_TAG_NAMES = {
    b"\xa9nam": "Judul",
    b"\xa9ART": "Artis",
    b"\xa9alb": "Album",
    b"\xa9day": "Tahun",
    b"\xa9cmt": "Komentar",
    b"\xa9gen": "Genre",
    b"\xa9too": "Perangkat/Encoder",
    b"\xa9wrt": "Penulis",
    b"\xa9cpy": "Hak Cipta",
    b"desc": "Deskripsi",
    b"\xa9xyz": "Lokasi/GPS",
    b"\xa9swr": "Software",
    b"gps ": "GPS",
}


def _decode_tag_value(name_atom):
    """
    Ambil nilai teks dari sebuah atom tag.

    Tag MP4/QuickTime biasanya berisi sub-atom 'data':
        [4 size][4 'data'][4 type][4 locale][payload teks]
    Karena atom tag bukan kontainer terdaftar, isinya ada di `name_atom.data`
    sebagai byte mentah; kita parse 'data' secara manual.
    """
    raw = name_atom.data
    if not raw:
        return ""
    # Cari sub-atom 'data' di dalam byte mentah.
    offset = 0
    while offset + 8 <= len(raw):
        sub_size = struct.unpack(">I", raw[offset:offset + 4])[0]
        sub_type = raw[offset + 4:offset + 8]
        if sub_size < 8 or offset + sub_size > len(raw):
            break
        if sub_type == b"data":
            body = raw[offset + 8:offset + sub_size]
            # Lewati 4 byte type + 4 byte locale.
            payload = body[8:] if len(body) > 8 else body
            return payload.decode("utf-8", "replace").strip("\x00").strip()
        offset += sub_size
    # Fallback: tag QuickTime dengan nilai langsung (16-bit size + 16-bit lang).
    text = raw[4:] if len(raw) > 4 else raw
    return text.decode("utf-8", "replace").strip("\x00").strip()


def read_metadata(input_path):
    """
    Baca nilai metadata deskriptif dari MP4/MOV.

    Return: list pasangan (nama, nilai), mis. [("Judul", "..."), ...].
    Mengembalikan list kosong jika tidak ada metadata deskriptif.
    """
    with open(input_path, "rb") as f:
        buf = f.read()
    atoms = _read_atoms(buf, 0, len(buf))
    result = []

    def walk(atom_list):
        for a in atom_list:
            if a.type in _MP4_TAG_NAMES:
                value = _decode_tag_value(a)
                if value:
                    result.append((_MP4_TAG_NAMES[a.type], value))
            elif len(a.type) == 4 and a.type[0] == 0xA9:
                # Tag '©xxxx' lain yang belum terdaftar namanya.
                value = _decode_tag_value(a)
                if value:
                    label = a.type.decode("latin-1", "replace")
                    result.append((label, value))
            if a.is_container and a.children:
                walk(a.children)

    walk(atoms)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Penggunaan: python mp4_cleaner.py <input.mp4> <output.mp4>")
        sys.exit(1)
    info = clean_mp4(sys.argv[1], sys.argv[2])
    print(f"Selesai. {info['removed']} atom metadata dihapus.")
    print(f"Ukuran: {info['input_size']} -> {info['output_size']} byte")
