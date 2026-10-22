from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# Survei dengan skor rata-rata <= batas ini otomatis menjadi tiket Red Alert.
BATAS_RED_ALERT = Decimal("2.0")


class Poliklinik(models.Model):
    nama = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nama"]
        verbose_name_plural = "Poliklinik"

    def __str__(self):
        return self.nama


class Dokter(models.Model):
    nama = models.CharField(max_length=150)
    poliklinik = models.ForeignKey(Poliklinik, on_delete=models.PROTECT, related_name="dokter")
    foto = models.ImageField(upload_to="dokter/", blank=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["nama"]
        verbose_name_plural = "Dokter"

    def __str__(self):
        return f"{self.nama} - {self.poliklinik}"

    @property
    def inisial(self):
        nama = self.nama.replace("drg.", "").replace("dr.", "").strip()
        return (nama[:1] or "?").upper()


class Pertanyaan(models.Model):
    poliklinik = models.ForeignKey(Poliklinik, on_delete=models.CASCADE, related_name="pertanyaan")
    teks = models.CharField(max_length=255)
    urutan = models.PositiveSmallIntegerField(default=0)
    aktif = models.BooleanField(default=True)

    class Meta:
        ordering = ["poliklinik", "urutan", "id"]
        verbose_name_plural = "Pertanyaan"

    def __str__(self):
        return f"[{self.poliklinik}] {self.teks}"


class OpsiJawaban(models.Model):
    pertanyaan = models.ForeignKey(Pertanyaan, on_delete=models.CASCADE, related_name="opsi")
    label = models.CharField(max_length=100)
    skor = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Bobot 1-5 (contoh: 5 = sangat baik, 3 = cukup, 1 = kurang)",
    )
    urutan = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["urutan", "-skor"]
        verbose_name_plural = "Opsi jawaban"

    def __str__(self):
        return f"{self.label} ({self.skor})"


class Survei(models.Model):
    dokter = models.ForeignKey(Dokter, on_delete=models.PROTECT, related_name="survei")
    nama_pasien = models.CharField(max_length=120)
    no_hp = models.CharField(max_length=20, blank=True)
    tanggal_kunjungan = models.DateField()
    saran = models.TextField(blank=True)
    skor_rata = models.DecimalField(max_digits=3, decimal_places=2)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dibuat"]
        verbose_name_plural = "Survei"

    def __str__(self):
        return f"Survei #{self.pk} - {self.dokter.nama} ({self.skor_rata})"


class Jawaban(models.Model):
    survei = models.ForeignKey(Survei, on_delete=models.CASCADE, related_name="jawaban")
    pertanyaan = models.ForeignKey(Pertanyaan, on_delete=models.PROTECT)
    opsi = models.ForeignKey(OpsiJawaban, on_delete=models.PROTECT)
    # Salinan bobot saat dijawab, supaya laporan lama tidak berubah jika bobot opsi diedit.
    skor = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name_plural = "Jawaban"


class Komplain(models.Model):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    STATUS = [
        (PENDING, "Pending"),
        (IN_PROGRESS, "In Progress"),
        (RESOLVED, "Resolved"),
    ]

    survei = models.OneToOneField(Survei, on_delete=models.CASCADE, related_name="komplain")
    status = models.CharField(max_length=12, choices=STATUS, default=PENDING)
    catatan_tindak_lanjut = models.TextField(blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diperbarui = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dibuat"]
        verbose_name_plural = "Komplain"

    def __str__(self):
        return f"Komplain #{self.pk} ({self.get_status_display()})"

    @property
    def alasan(self):
        return "Skor rendah" if self.survei.skor_rata <= BATAS_RED_ALERT else "Umpan balik kritis"
