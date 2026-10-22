from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from .models import BATAS_RED_ALERT, Dokter, Jawaban, Komplain, OpsiJawaban, Poliklinik, Survei

# Kata yang membuat saran pasien dianggap "umpan balik kritis" dan otomatis jadi tiket Red Alert,
# walaupun skor rata-ratanya tinggi. Ubah daftar ini sesuai kebutuhan rumah sakit.
KATA_KRITIS = [
    "kecewa", "mengecewakan", "marah", "kasar", "tidak ramah", "malpraktik",
    "komplain", "tidak puas", "menyesal", "jorok", "kotor", "buruk sekali",
]

PERIODE = [
    ("bulan_ini", "Bulan ini"),
    ("3_bulan", "3 bulan terakhir"),
    ("tahun_ini", "Tahun ini"),
    ("semua", "Semua waktu"),
]

BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def mulai_periode(kode):
    """Ubah kode periode (mis. 'bulan_ini') menjadi batas awal waktu, atau None untuk semua waktu."""
    sekarang = timezone.localtime()
    awal_hari = dict(hour=0, minute=0, second=0, microsecond=0)
    if kode == "bulan_ini":
        return sekarang.replace(day=1, **awal_hari)
    if kode == "3_bulan":
        return sekarang - timedelta(days=90)
    if kode == "tahun_ini":
        return sekarang.replace(month=1, day=1, **awal_hari)
    return None


def hitung_skor_rata(daftar_skor):
    """Rata-rata skor = total skor semua jawaban / jumlah pertanyaan yang dijawab."""
    if not daftar_skor:
        raise ValueError("Tidak ada jawaban untuk dihitung.")
    rata = Decimal(sum(daftar_skor)) / Decimal(len(daftar_skor))
    return rata.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def mengandung_kata_kritis(saran):
    teks = (saran or "").lower()
    return any(kata in teks for kata in KATA_KRITIS)


@transaction.atomic
def simpan_survei(*, dokter, nama_pasien, no_hp, tanggal_kunjungan, jawaban, saran):
    """Simpan satu survei lengkap.

    `jawaban` berbentuk {pertanyaan_id: opsi_id}. Opsi harus milik pertanyaan tersebut,
    jika tidak, OpsiJawaban.DoesNotExist akan muncul.
    """
    daftar_opsi = [
        OpsiJawaban.objects.select_related("pertanyaan").get(pk=opsi_id, pertanyaan_id=pertanyaan_id)
        for pertanyaan_id, opsi_id in jawaban.items()
    ]
    skor_rata = hitung_skor_rata([o.skor for o in daftar_opsi])

    survei = Survei.objects.create(
        dokter=dokter,
        nama_pasien=nama_pasien,
        no_hp=no_hp,
        tanggal_kunjungan=tanggal_kunjungan,
        saran=saran,
        skor_rata=skor_rata,
    )
    Jawaban.objects.bulk_create(
        [Jawaban(survei=survei, pertanyaan=o.pertanyaan, opsi=o, skor=o.skor) for o in daftar_opsi]
    )
    if skor_rata <= BATAS_RED_ALERT or mengandung_kata_kritis(saran):
        Komplain.objects.create(survei=survei)
    return survei


def ringkasan(sejak=None):
    qs = Survei.objects.all()
    if sejak:
        qs = qs.filter(dibuat__gte=sejak)
    agregat = qs.aggregate(total=Count("id"), rata=Avg("skor_rata"))
    komplain_aktif = Komplain.objects.exclude(status=Komplain.RESOLVED).count()
    return {"total": agregat["total"], "rata": agregat["rata"], "komplain_aktif": komplain_aktif}


def per_poli(sejak=None):
    filter_waktu = Q(dokter__survei__dibuat__gte=sejak) if sejak else None
    return Poliklinik.objects.annotate(
        jumlah=Count("dokter__survei", filter=filter_waktu),
        rata=Avg("dokter__survei__skor_rata", filter=filter_waktu),
    ).order_by(F("rata").desc(nulls_last=True), "nama")


def leaderboard(poli=None, sejak=None, poli_id=None, cari=None):
    """Daftar dokter berurutan dari skor rata-rata tertinggi (hanya yang punya responden)."""
    filter_waktu = Q(survei__dibuat__gte=sejak) if sejak else None
    qs = (
        Dokter.objects.select_related("poliklinik")
        .annotate(
            jumlah=Count("survei", filter=filter_waktu),
            rata=Avg("survei__skor_rata", filter=filter_waktu),
        )
        .filter(jumlah__gt=0)
    )
    if poli:
        qs = qs.filter(poliklinik__nama__icontains=poli)
    if poli_id:
        qs = qs.filter(poliklinik_id=poli_id)
    if cari:
        qs = qs.filter(nama__icontains=cari)
    return qs.order_by("-rata", "-jumlah", "nama")


def tren(granularitas="harian"):
    """Titik-titik grafik tren kepuasan: 30 hari, 12 minggu, atau 12 bulan terakhir."""
    fungsi, batas = {
        "harian": (TruncDate, 30),
        "mingguan": (TruncWeek, 12),
        "bulanan": (TruncMonth, 12),
    }[granularitas]
    baris = list(
        Survei.objects.annotate(periode=fungsi("dibuat"))
        .values("periode")
        .annotate(n=Count("id"), rata=Avg("skor_rata"))
        .order_by("periode")
    )[-batas:]

    hasil = []
    for b in baris:
        p = b["periode"]
        label = f"{BULAN[p.month - 1]} {p.year}" if granularitas == "bulanan" else f"{p.day} {BULAN[p.month - 1]}"
        hasil.append({"label": label, "n": b["n"], "rata": b["rata"], "tinggi": round(float(b["rata"]) / 5 * 100)})
    return hasil
