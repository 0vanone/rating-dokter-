from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from survey.models import Komplain


class Command(BaseCommand):
    help = "Ubah status komplain dan/atau tambah catatan tindak lanjut."

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)
        parser.add_argument("--status", choices=[Komplain.PENDING, Komplain.IN_PROGRESS, Komplain.RESOLVED])
        parser.add_argument("--catatan", help="Catatan tindak lanjut (ditambahkan ke log dengan waktu).")

    def handle(self, *args, **opts):
        if not opts["status"] and not opts["catatan"]:
            raise CommandError("Isi --status dan/atau --catatan.")
        try:
            k = Komplain.objects.get(pk=opts["id"])
        except Komplain.DoesNotExist:
            raise CommandError("Komplain tidak ditemukan.")

        if opts["status"]:
            k.status = opts["status"]
        if opts["catatan"]:
            waktu = timezone.localtime().strftime("%Y-%m-%d %H:%M")
            k.catatan_tindak_lanjut = (k.catatan_tindak_lanjut + "\n" if k.catatan_tindak_lanjut else "") + (
                f"[{waktu}] {opts['catatan']}"
            )
        k.save()
        self.stdout.write(self.style.SUCCESS(f"Komplain #{k.pk} sekarang: {k.get_status_display()}"))
