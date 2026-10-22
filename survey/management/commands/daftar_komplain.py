from django.core.management.base import BaseCommand, CommandError

from survey.cli_utils import cetak_tabel, fmt_skor, ringkas
from survey.models import Komplain


class Command(BaseCommand):
    help = "Daftar tiket komplain (Red Alert) dari ulasan dengan skor rendah."

    def add_arguments(self, parser):
        parser.add_argument("--status", choices=[Komplain.PENDING, Komplain.IN_PROGRESS, Komplain.RESOLVED])
        parser.add_argument("--id", type=int, help="Tampilkan detail lengkap satu komplain.")

    def handle(self, *args, **opts):
        qs = Komplain.objects.select_related("survei__dokter__poliklinik")

        if opts["id"]:
            k = qs.filter(pk=opts["id"]).first()
            if k is None:
                raise CommandError("Komplain tidak ditemukan.")
            s = k.survei
            self.stdout.write(f"Komplain #{k.pk}  [{k.get_status_display()}]")
            self.stdout.write(f"Pasien   : {s.nama_pasien}  HP: {s.no_hp or '-'}")
            self.stdout.write(f"Kunjungan: {s.tanggal_kunjungan}  {s.dokter.nama} ({s.dokter.poliklinik.nama})")
            self.stdout.write(f"Skor     : {fmt_skor(s.skor_rata)}")
            self.stdout.write(f"Saran    : {s.saran or '(kosong)'}")
            self.stdout.write(f"Tindak lanjut:\n{k.catatan_tindak_lanjut or '(belum ada)'}")
            return

        if opts["status"]:
            qs = qs.filter(status=opts["status"])
        baris = [
            [k.pk, k.survei.tanggal_kunjungan, k.survei.dokter.nama, k.survei.dokter.poliklinik.nama,
             fmt_skor(k.survei.skor_rata), k.get_status_display(), ringkas(k.survei.saran, 40)]
            for k in qs
        ]
        if not baris:
            self.stdout.write("Tidak ada komplain.")
            return
        cetak_tabel(self.stdout, ["ID", "Kunjungan", "Dokter", "Poli", "Skor", "Status", "Saran"], baris)
