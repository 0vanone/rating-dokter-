from django.core.management.base import BaseCommand
from django.db import transaction

from survey.models import Dokter, OpsiJawaban, Pertanyaan, Poliklinik

# 5 pertanyaan per poli, berbeda untuk tiap poli.
# Format: (teks pertanyaan, [(label, skor), ...])
KUESIONER = {
    "Poli Gigi": [
        ("Bagaimana kebersihan alat medis yang digunakan?",
         [("Sangat bersih & higienis", 5), ("Cukup bersih", 3), ("Perlu diperbaiki", 1)]),
        ("Bagaimana kelembutan tindakan dokter gigi?",
         [("Sangat nyaman", 5), ("Tindakan lembut", 3), ("Agak linu", 1)]),
        ("Seberapa jelas instruksi perawatan setelah tindakan?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
        ("Seberapa jelas dokter menjelaskan tindakan sebelum dimulai?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
        ("Bagaimana dokter menangani rasa tidak nyaman selama tindakan?",
         [("Sangat diperhatikan", 5), ("Cukup diperhatikan", 3), ("Kurang diperhatikan", 1)]),
    ],
    "Poli Anak": [
        ("Bagaimana pendekatan dan kesabaran dokter terhadap anak?",
         [("Sangat ramah & sabar", 5), ("Ramah", 3), ("Kurang ramah", 1)]),
        ("Seberapa jelas penjelasan dosis obat untuk orang tua?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
        ("Bagaimana kenyamanan fasilitas anak?",
         [("Nyaman & bersih", 5), ("Cukup nyaman", 3), ("Perlu diperbaiki", 1)]),
        ("Seberapa jelas dokter menjelaskan kondisi anak kepada orang tua?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
        ("Seberapa jelas dokter menjelaskan tanda bahaya yang perlu diwaspadai di rumah?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Tidak dijelaskan", 1)]),
    ],
    "Poli Umum": [
        ("Seberapa teliti dokter mendengarkan keluhan Anda?",
         [("Sangat teliti", 5), ("Cukup teliti", 3), ("Kurang teliti", 1)]),
        ("Seberapa jelas penjelasan diagnosa dan resep?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
        ("Bagaimana ketepatan waktu jam praktik?",
         [("Tepat waktu", 5), ("Sedikit terlambat", 3), ("Menunggu lama", 1)]),
        ("Seberapa teliti dokter melakukan pemeriksaan?",
         [("Sangat teliti", 5), ("Cukup teliti", 3), ("Kurang teliti", 1)]),
        ("Seberapa jelas saran gaya hidup dan jadwal kontrol lanjutan?",
         [("Sangat jelas", 5), ("Cukup jelas", 3), ("Kurang jelas", 1)]),
    ],
}

DOKTER = [
    ("dr. Contoh Satu", "Poli Gigi"),
    ("dr. Contoh Dua", "Poli Anak"),
    ("dr. Contoh Tiga", "Poli Umum"),
    ("dr. Contoh Empat", "Poli Gigi"),
]


class Command(BaseCommand):
    help = "Isi data contoh (poliklinik, dokter, bank pertanyaan). Aman dijalankan berulang."

    @transaction.atomic
    def handle(self, *args, **opts):
        poli = {n: Poliklinik.objects.get_or_create(nama=n)[0] for n in KUESIONER}

        for nama_poli, daftar in KUESIONER.items():
            for urutan, (teks, opsi) in enumerate(daftar, start=1):
                p, dibuat = Pertanyaan.objects.get_or_create(
                    poliklinik=poli[nama_poli], teks=teks, defaults={"urutan": urutan}
                )
                if not dibuat:
                    p.urutan = urutan
                    p.aktif = True
                    p.save()
                if dibuat:
                    for u, (label, skor) in enumerate(opsi, start=1):
                        OpsiJawaban.objects.create(pertanyaan=p, label=label, skor=skor, urutan=u)

            # Pertanyaan lama di poli ini yang tidak ada di daftar dinonaktifkan (tidak dihapus,
            # supaya jawaban survei lama tetap utuh).
            Pertanyaan.objects.filter(poliklinik=poli[nama_poli]).exclude(
                teks__in=[teks for teks, _ in daftar]
            ).update(aktif=False)

        for nama, nama_poli in DOKTER:
            Dokter.objects.get_or_create(nama=nama, defaults={"poliklinik": poli[nama_poli]})

        self.stdout.write(self.style.SUCCESS("Data contoh siap. Ganti dengan data asli lewat /admin/."))
