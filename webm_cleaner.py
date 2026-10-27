"""
webm_cleaner.py
---------------
Pembersih metadata untuk file WEBM / Matroska (MKV) menggunakan Python murni,
TANPA dependensi eksternal.

WEBM/MKV memakai struktur EBML (mirip XML biner). Elemen penting:
  Segment (0x18538067)
    Info (0x1549A966)
      Title      (0x7BA9)
      MuxingApp  (0x4D80)   -> mis. "Chrome"
      WritingApp (0x5741)   -> mis. "Chrome"
      DateUTC    (0x4461)
    Tags (0x1254C367)       -> tag metadata bebas

Strategi (in-place, aman & menjaga ukuran file):
  Elemen metadata ditimpa dengan elemen 'Void' (ID 0xEC). Void adalah elemen
  pengisi legal di EBML yang diabaikan pemutar. Karena panjang total tidak
  berubah, semua offset & ukuran elemen induk tetap valid tanpa perlu dihitung
  ulang. Ini membuat file tetap dapat diputar.

Yang dibersihkan:
  - Seluruh elemen 'Tags' (di-Void-kan).
  - Isi 'Title', 'MuxingApp', 'WritingApp', 'DateUTC' di dalam 'Info'
    (di-Void-kan sehingga nilainya hilang).
"""

import struct

# ----- ID elemen EBML (sebagai integer, termasuk marker length-nya) -----
ID_SEGMENT = 0x18538067
ID_INFO = 0x1549A966
ID_TAGS = 0x1254C367
ID_VOID = 0xEC

# Elemen dalam Info yang nilainya dianggap metadata & akan dihapus.
INFO_META_IDS = {
    0x7BA9,  # Title
    0x4D80,  # MuxingApp
    0x5741,  # WritingApp
    0x4461,  # DateUTC
}

EBML_HEADER = 0x1A45DFA3  # magic EBML di awal file WEBM/MKV


def _read_vint(buf, pos, is_id):
    """
    Baca EBML variable-length integer mulai dari posisi `pos`.
    - is_id=True  : nilai dikembalikan APA ADANYA (marker length tetap), khusus ID.
    - is_id=False : marker length di-mask (untuk ukuran/size).
    Return: (nilai, panjang_byte, pos_baru).
    """
    first = buf[pos]
    if first == 0:
        raise ValueError("VINT tidak valid (byte 0).")
    # Jumlah byte ditentukan posisi bit tertinggi yang set.
    mask = 0x80
    length = 1
    while not (first & mask):
        mask >>= 1
        length += 1
        if length > 8:
            raise ValueError("VINT terlalu panjang.")
    raw = buf[pos:pos + length]
    value = int.from_bytes(raw, "big")
    if not is_id:
        # Hapus bit marker panjang untuk mendapatkan nilai size sebenarnya.
        value &= (1 << (7 * length)) - 1
    return value, length, pos + length


def _overwrite_with_void(buf, start, total_len):
    """
    Timpa rentang buf[start:start+total_len] dengan satu elemen Void (0xEC)
    yang panjangnya persis sama. Mengubah `buf` (bytearray) di tempat.

    Struktur Void: [0xEC][size-vint][payload]
    Kita pilih lebar size-vint agar header + payload == total_len.
    """
    # Coba lebar size 1..8 byte; cari yang pas.
    for size_len in range(1, 9):
        header = 1 + size_len  # 1 byte ID (0xEC) + size vint
        payload = total_len - header
        if payload < 0:
            continue
        # size vint harus mampu menampung nilai `payload` pada `size_len` byte.
        max_val = (1 << (7 * size_len)) - 1
        if payload <= max_val:
            buf[start] = ID_VOID
            # Encode size sebagai vint dengan lebar size_len.
            marker = 1 << (7 * size_len)
            size_field = marker | payload
            buf[start + 1:start + 1 + size_len] = size_field.to_bytes(size_len, "big")
            # Payload dibiarkan apa adanya (byte lama) -> diabaikan karena Void.
            # Namun kita nolkan agar tidak ada sisa metadata yang terbaca.
            for i in range(start + header, start + total_len):
                buf[i] = 0x00
            return
    raise ValueError(f"Tidak bisa membuat Void untuk panjang {total_len}.")


def _walk(buf, start, end, removed):
    """
    Telusuri elemen EBML pada rentang [start, end).
    Jika menemukan Tags -> di-Void-kan seluruhnya.
    Jika menemukan Info -> masuk & bersihkan elemen metadata di dalamnya.
    `removed` adalah list untuk mencatat apa yang dihapus.
    """
    pos = start
    while pos < end:
        elem_start = pos
        try:
            elem_id, _, pos = _read_vint(buf, pos, is_id=True)
            size, _, pos = _read_vint(buf, pos, is_id=False)
        except (IndexError, ValueError):
            break
        content_start = pos
        content_end = content_start + size
        if content_end > end:
            content_end = end  # jaga-jaga terhadap ukuran tak terbatas

        total_len = content_end - elem_start

        if elem_id == ID_TAGS:
            _overwrite_with_void(buf, elem_start, total_len)
            removed.append("Tags")
        elif elem_id == ID_SEGMENT:
            # Segment: masuk rekursif ke isinya.
            _walk(buf, content_start, content_end, removed)
        elif elem_id == ID_INFO:
            _clean_info(buf, content_start, content_end, removed)

        pos = content_end
    return removed


def _clean_info(buf, start, end, removed):
    """Dalam elemen Info, Void-kan elemen Title/MuxingApp/WritingApp/DateUTC."""
    pos = start
    names = {0x7BA9: "Title", 0x4D80: "MuxingApp",
             0x5741: "WritingApp", 0x4461: "DateUTC"}
    while pos < end:
        elem_start = pos
        try:
            elem_id, _, pos = _read_vint(buf, pos, is_id=True)
            size, _, pos = _read_vint(buf, pos, is_id=False)
        except (IndexError, ValueError):
            break
        content_end = pos + size
        if content_end > end:
            content_end = end
        if elem_id in INFO_META_IDS:
            total_len = content_end - elem_start
            _overwrite_with_void(buf, elem_start, total_len)
            removed.append("Info/" + names.get(elem_id, hex(elem_id)))
        pos = content_end


def clean_webm(input_path, output_path):
    """
    Hapus metadata dari file WEBM/MKV dan tulis ke output_path.
    Return dict: {'removed': [daftar elemen], 'input_size', 'output_size'}.
    Raise ValueError jika bukan file EBML valid.
    """
    with open(input_path, "rb") as f:
        buf = bytearray(f.read())

    if len(buf) < 4 or int.from_bytes(buf[0:4], "big") != EBML_HEADER:
        raise ValueError("Bukan file WEBM/MKV (header EBML 0x1A45DFA3 tidak ditemukan).")

    removed = []
    _walk(buf, 0, len(buf), removed)

    with open(output_path, "wb") as f:
        f.write(buf)

    return {
        "removed": removed,
        "input_size": len(buf),
        "output_size": len(buf),
    }


def list_metadata(input_path):
    """Kembalikan daftar elemen metadata (Tags & field Info) yang terdeteksi."""
    with open(input_path, "rb") as f:
        buf = f.read()
    found = []
    names = {0x7BA9: "Title", 0x4D80: "MuxingApp",
             0x5741: "WritingApp", 0x4461: "DateUTC"}

    def scan(start, end, in_info=False):
        pos = start
        while pos < end:
            es = pos
            try:
                eid, _, pos = _read_vint(buf, pos, is_id=True)
                size, _, pos = _read_vint(buf, pos, is_id=False)
            except (IndexError, ValueError):
                break
            ce = pos + size
            if ce > end:
                ce = end
            if eid == ID_TAGS:
                found.append("Tags")
            elif eid == ID_SEGMENT:
                scan(pos, ce)
            elif eid == ID_INFO:
                scan(pos, ce, in_info=True)
            elif in_info and eid in INFO_META_IDS:
                val = buf[pos:ce]
                text = val.decode("utf-8", "replace") if eid != 0x4461 else val.hex()
                found.append(f"Info/{names.get(eid)}={text!r}")
            pos = ce

    scan(0, len(buf))
    return found


def read_metadata(input_path):
    """
    Baca metadata WEBM/MKV sebagai list pasangan (nama, nilai), seragam
    dengan mp4_cleaner.read_metadata.
    """
    result = []
    for item in list_metadata(input_path):
        if item == "Tags":
            result.append(("Tags", "(ada tag metadata)"))
        elif item.startswith("Info/") and "=" in item:
            name, _, value = item.partition("=")
            # value berupa repr string; buang tanda kutip terluarnya.
            value = value.strip()
            if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
                value = value[1:-1]
            result.append((name.replace("Info/", ""), value))
        else:
            result.append((item, ""))
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Penggunaan: python webm_cleaner.py <input.webm> <output.webm>")
        sys.exit(1)
    print("Sebelum:", list_metadata(sys.argv[1]))
    info = clean_webm(sys.argv[1], sys.argv[2])
    print("Dihapus:", info["removed"])
    print("Sesudah:", list_metadata(sys.argv[2]))
