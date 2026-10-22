from django.core.management.base import BaseCommand

from survey import services
from survey.cli_utils import cetak_tabel, fmt_skor, parse_tanggal


class Command(BaseCommand):
    help = "Peringkat kinerja dokter berdasarkan skor rerata (tertinggi ke terendah)."

    def add_arguments(self, parser):
        parser.add_argument("--poli", help="Filter nama poliklinik (sebagian nama boleh), contoh: gigi")
        parser.add_argument("--sejak", help="Hitung mulai tanggal ini (YYYY-MM-DD).")
        parser.add_argument("--cari", help="Cari nama dokter.")

    def handle(self, *args, **opts):
        qs = services.leaderboard(poli=opts["poli"], sejak=parse_tanggal(opts["sejak"]))
        if opts["cari"]:
            qs = qs.filter(nama__icontains=opts["cari"])

        baris = [
            [i, d.pk, d.nama, d.poliklinik.nama, d.jumlah, fmt_skor(d.rata)]
            for i, d in enumerate(qs, start=1)
        ]
        if not baris:
            self.stdout.write("Belum ada data survei untuk filter ini.")
            return
        cetak_tabel(self.stdout, ["#", "ID", "Dokter", "Poliklinik", "Responden", "Skor"], baris)
