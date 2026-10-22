from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Buat 1 QR code pusat rumah sakit dalam resolusi tinggi (PNG atau SVG)."

    def add_arguments(self, parser):
        parser.add_argument("--url", help="Alamat survei. Default: SURVEY_BASE_URL di settings.")
        parser.add_argument("--out", default="qr_universal.png", help="File keluaran (.png atau .svg).")

    def handle(self, *args, **opts):
        try:
            import qrcode
            import qrcode.constants
            from qrcode.image.svg import SvgPathImage
        except ImportError:
            raise CommandError("Pasang dulu: pip install 'qrcode[pil]'")

        url = opts["url"] or settings.SURVEY_BASE_URL
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=20,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        if opts["out"].lower().endswith(".svg"):
            gambar = qr.make_image(image_factory=SvgPathImage)
        else:
            gambar = qr.make_image(fill_color="black", back_color="white")
        gambar.save(opts["out"])

        self.stdout.write(self.style.SUCCESS(f"QR tersimpan di {opts['out']} -> {url}"))
