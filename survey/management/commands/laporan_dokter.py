from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Count

from survey.cli_utils import cetak_tabel, fmt_skor
from survey.models import Dokter, Jawaban, Survei


class Command(BaseCommand):
    help = "Laporan personal satu dokter: skor per indikator dan saran terbaru dari pasien."

    def add_arguments(self, parser):
        parser.add_argument("dokter", help="ID dokter atau sebagian nama dokter.")
        parser.add_argument("--saran", type=int, default=10, help="Jumlah saran terbaru yang ditampilkan.")

    def handle(self, *args, **opts):
        kunci = opts["dokter"].strip()
        qs = Dokter.objects.select_related("poliklinik")
        dokter = qs.filter(pk=int(kunci)).first() if kunci.isdigit() else None
        if dokter is None:
            cocok = list(qs.filter(nama__icontains=kunci))
            if not cocok:
                raise CommandError("Dokter tidak ditemukan.")
            if len(cocok) > 1:
                daftar = ", ".join(f"{d.pk}:{d.nama}" for d in cocok)
                raise CommandError(f"Ada beberapa dokter yang cocok ({daftar}). Gunakan ID.")
            dokter = cocok[0]

        survei = Survei.objects.filter(dokter=dokter)
        agregat = survei.aggregate(n=Count("id"), rata=Avg("skor_rata"))

        self.stdout.write(f"{dokter.nama} - {dokter.poliklinik.nama}")
        self.stdout.write(f"Responden: {agregat['n']}   Skor rerata: {fmt_skor(agregat['rata'])} / 5.00")
        self.stdout.write("")

        per_indikator = (
            Jawaban.objects.filter(survei__dokter=dokter)
            .values("pertanyaan__teks")
            .annotate(n=Count("id"), rata=Avg("skor"))
            .order_by("pertanyaan__urutan", "pertanyaan__id")
        )
        cetak_tabel(
            self.stdout,
            ["Indikator", "Jawaban", "Skor"],
            [[r["pertanyaan__teks"], r["n"], fmt_skor(r["rata"])] for r in per_indikator],
        )

        self.stdout.write("")
        self.stdout.write("Saran terbaru dari pasien:")
        terbaru = survei.exclude(saran="")[: opts["saran"]]
        if not terbaru:
            self.stdout.write("  (belum ada saran)")
        for s in terbaru:
            self.stdout.write(f"  [{s.dibuat:%Y-%m-%d}] {s.saran}")
