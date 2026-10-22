import csv

from django.core.management.base import BaseCommand, CommandError

from survey.cli_utils import aman_sel, parse_tanggal
from survey.models import Survei

HEADER = ["ID", "Waktu", "Poliklinik", "Dokter",
          "Nama pasien", "No HP", "Tanggal kunjungan", "Skor rata-rata", "Saran"]


class Command(BaseCommand):
    help = "Ekspor rekap survei ke Excel (.xlsx) atau CSV untuk bahan rapat."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="laporan_survei.xlsx", help="File keluaran (.xlsx atau .csv).")
        parser.add_argument("--sejak", help="Mulai tanggal (YYYY-MM-DD).")

    def handle(self, *args, **opts):
        qs = Survei.objects.select_related("dokter__poliklinik").order_by("dibuat")
        sejak = parse_tanggal(opts["sejak"])
        if sejak:
            qs = qs.filter(dibuat__gte=sejak)

        baris = [
            [
                s.pk,
                s.dibuat.astimezone().strftime("%Y-%m-%d %H:%M"),
                s.dokter.poliklinik.nama,
                s.dokter.nama,
                aman_sel(s.nama_pasien),
                aman_sel(s.no_hp),
                s.tanggal_kunjungan.isoformat(),
                float(s.skor_rata),
                aman_sel(s.saran),
            ]
            for s in qs
        ]

        out = opts["out"]
        if out.lower().endswith(".csv"):
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                tulis = csv.writer(f)
                tulis.writerow(HEADER)
                tulis.writerows(baris)
        elif out.lower().endswith(".xlsx"):
            try:
                from openpyxl import Workbook
            except ImportError:
                raise CommandError("Pasang dulu: pip install openpyxl")
            wb = Workbook()
            ws = wb.active
            ws.title = "Survei"
            ws.append(HEADER)
            for b in baris:
                ws.append(b)
            wb.save(out)
        else:
            raise CommandError("Ekstensi file harus .xlsx atau .csv")

        self.stdout.write(self.style.SUCCESS(f"{len(baris)} baris diekspor ke {out}"))
