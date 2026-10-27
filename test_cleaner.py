"""
test_cleaner.py
Uji otomatis: buat file MP4 sintetis dengan atom metadata (moov>udta>meta),
jalankan clean_mp4, lalu pastikan atom metadata hilang & struktur tetap valid.
"""
import struct
import os
import mp4_cleaner


def box(atom_type, payload):
    return struct.pack(">I", len(payload) + 8) + atom_type + payload


def build_sample_mp4(path):
    # ftyp
    ftyp = box(b"ftyp", b"isom" + struct.pack(">I", 0x200) + b"isomiso2mp41")

    # Metadata di dalam moov>udta: 'meta' (full box: 4 byte version/flags) + ilst
    name_tag = box(b"\xa9nam", b"\x00\x00\x00\x0fdata-JUDUL-RAHASIA")
    ilst = box(b"ilst", name_tag)
    meta = box(b"meta", struct.pack(">I", 0) + ilst)  # full box prefix
    udta = box(b"udta", meta)

    # trak minimal (hanya placeholder agar moov punya anak selain udta)
    mvhd = box(b"mvhd", b"\x00" * 100)
    trak = box(b"trak", box(b"tkhd", b"\x00" * 80))

    moov = box(b"moov", mvhd + trak + udta)

    # mdat berisi data dummy (pengganti stream media)
    mdat = box(b"mdat", b"\x00\x11\x22\x33" * 16)

    with open(path, "wb") as f:
        f.write(ftyp + moov + mdat)


def run():
    sample = "sample.mp4"
    cleaned = "sample_clean.mp4"
    build_sample_mp4(sample)

    before = mp4_cleaner.list_metadata_atoms(sample)
    print("Metadata atom SEBELUM:", before)
    assert before, "Seharusnya ada atom metadata di file contoh!"

    info = mp4_cleaner.clean_mp4(sample, cleaned)
    print("clean_mp4 ->", info)

    after = mp4_cleaner.list_metadata_atoms(cleaned)
    print("Metadata atom SESUDAH:", after)
    assert not after, f"Masih ada metadata: {after}"

    # Pastikan atom penting masih ada (ftyp, moov, mdat, trak, mvhd).
    with open(cleaned, "rb") as f:
        buf = f.read()
    atoms = mp4_cleaner._read_atoms(buf, 0, len(buf))
    top = {a.type for a in atoms}
    print("Atom top-level sesudah:", sorted(t.decode("latin-1") for t in top))
    assert b"ftyp" in top and b"moov" in top and b"mdat" in top, "Struktur rusak!"

    moov = next(a for a in atoms if a.type == b"moov")
    moov_children = {c.type for c in moov.children}
    assert b"mvhd" in moov_children and b"trak" in moov_children, "Isi moov hilang!"
    assert b"udta" not in moov_children, "udta belum terhapus!"

    # Validasi konsistensi ukuran: total serial = ukuran file.
    assert info["output_size"] == len(buf) == os.path.getsize(cleaned)

    print("\nSEMUA PENGUJIAN LULUS. Metadata terhapus, struktur video utuh.")

    os.remove(sample)
    os.remove(cleaned)


if __name__ == "__main__":
    run()
