from datetime import datetime

from django.core.management.base import CommandError
from django.utils import timezone


def parse_tanggal(teks):
    """Ubah 'YYYY-MM-DD' menjadi datetime aware, atau None jika kosong."""
    if not teks:
        return None
    try:
        return timezone.make_aware(datetime.strptime(teks, "%Y-%m-%d"))
    except ValueError:
        raise CommandError("Format tanggal harus YYYY-MM-DD, contoh: 2026-10-01")


def fmt_skor(nilai):
    return "-" if nilai is None else f"{float(nilai):.2f}"


def cetak_tabel(stdout, header, baris):
    """Cetak tabel teks sederhana tanpa dependensi tambahan."""
    baris = [[str(sel) for sel in b] for b in baris]
    lebar = [max(len(str(x)) for x in kolom) for kolom in zip(header, *baris)]
    garis = "  ".join("-" * w for w in lebar)
    stdout.write("  ".join(str(h).ljust(w) for h, w in zip(header, lebar)))
    stdout.write(garis)
    for b in baris:
        stdout.write("  ".join(sel.ljust(w) for sel, w in zip(b, lebar)))


def ringkas(teks, panjang=60):
    teks = " ".join((teks or "").split())
    return teks if len(teks) <= panjang else teks[: panjang - 1] + "…"


def aman_sel(nilai):
    """Cegah formula injection saat teks pasien dibuka di Excel."""
    teks = "" if nilai is None else str(nilai)
    return "'" + teks if teks.startswith(("=", "+", "-", "@")) else teks
