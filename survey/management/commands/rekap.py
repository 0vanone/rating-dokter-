from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek

from survey import services
from survey.cli_utils import cetak_tabel, fmt_skor, parse_tanggal
from survey.models import Poliklinik, Survei


class Command(BaseCommand):
    help = "Ringkasan eksekutif: total survei, skor rerata RS, komplain aktif, skor per poli, dan tren."

    def add_arguments(self, parser):
        parser.add_argument("--sejak", help="Hanya hitung survei mulai tanggal ini (YYYY-MM-DD).")
        parser.add_argument("--tren", choices=["harian", "mingguan", "bulanan"], help="Tampilkan tren kepuasan.")

    def handle(self, *args, **opts):
        sejak = parse_tanggal(opts["sejak"])
        data = services.ringkasan(sejak)

        self.stdout.write(f"Total survei masuk   : {data['total']}")
        self.stdout.write(f"Skor rerata RS       : {fmt_skor(data['rata'])} / 5.00")
        self.stdout.write(f"Total komplain aktif : {data['komplain_aktif']}")
        self.stdout.write("")

        filter_waktu = Q(dokter__survei__dibuat__gte=sejak) if sejak else None
        per_poli = Poliklinik.objects.annotate(
            jumlah=Count("dokter__survei", filter=filter_waktu),
            rata=Avg("dokter__survei__skor_rata", filter=filter_waktu),
        ).order_by("-rata")
        cetak_tabel(
            self.stdout,
            ["Poliklinik", "Responden", "Skor rerata"],
            [[p.nama, p.jumlah, fmt_skor(p.rata)] for p in per_poli],
        )

        if opts["tren"]:
            fungsi = {"harian": TruncDate, "mingguan": TruncWeek, "bulanan": TruncMonth}[opts["tren"]]
            format_periode = "%Y-%m" if opts["tren"] == "bulanan" else "%Y-%m-%d"
            qs = Survei.objects.all()
            if sejak:
                qs = qs.filter(dibuat__gte=sejak)
            tren = (
                qs.annotate(periode=fungsi("dibuat"))
                .values("periode")
                .annotate(n=Count("id"), rata=Avg("skor_rata"))
                .order_by("periode")
            )
            self.stdout.write("")
            self.stdout.write(f"Tren kepuasan ({opts['tren']})")
            cetak_tabel(
                self.stdout,
                ["Periode", "Survei", "Skor", "Grafik"],
                [
                    [t["periode"].strftime(format_periode), t["n"], fmt_skor(t["rata"]),
                     "█" * round(float(t["rata"]) * 4)]
                    for t in tren
                ],
            )
