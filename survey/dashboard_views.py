from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import reports, services
from .forms import AkunBaruForm, DokterForm, OpsiFormSet, PertanyaanForm, PoliForm
from .models import Dokter, Komplain, Pertanyaan, Poliklinik

User = get_user_model()
GRANULARITAS = ("harian", "mingguan", "bulanan")


# ---------- pembantu ----------

def staff_required(view):
    """Hanya akun staf yang sudah login yang boleh membuka dashboard."""
    @wraps(view)
    def dibungkus(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("dashboard:masuk"))
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return dibungkus


def tampil(request, template, konteks, menu):
    konteks["menu"] = menu
    konteks["nav_komplain"] = Komplain.objects.filter(status=Komplain.PENDING).count()
    return render(request, template, konteks)


def _angka(nilai):
    nilai = (nilai or "").strip()
    return int(nilai) if nilai.isdigit() else None


def _periode(request, bawaan):
    kode = request.GET.get("periode", bawaan)
    return kode if kode in dict(services.PERIODE) else bawaan


def _hapus(request, objek, kembali, nama):
    try:
        objek.delete()
        messages.success(request, f"{nama} dihapus.")
    except ProtectedError:
        messages.error(
            request,
            f"{nama} tidak bisa dihapus karena sudah dipakai data lain (dokter atau hasil survei). "
            "Nonaktifkan saja lewat tombol Ubah jika perlu.",
        )
    return redirect(kembali)


# ---------- A. Ringkasan ----------

@staff_required
def ringkasan(request):
    periode = _periode(request, "bulan_ini")
    granular = request.GET.get("tren", "harian")
    if granular not in GRANULARITAS:
        granular = "harian"
    sejak = services.mulai_periode(periode)

    poli = list(services.per_poli(sejak))
    for p in poli:
        p.lebar = round(float(p.rata) / 5 * 100) if p.rata else 0

    return tampil(request, "dashboard/ringkasan.html", {
        "periode": periode,
        "daftar_periode": services.PERIODE,
        "label_periode": dict(services.PERIODE)[periode],
        "granular": granular,
        "data": services.ringkasan(sejak),
        "tren": services.tren(granular),
        "poli": poli,
        "terbaru": Komplain.objects.exclude(status=Komplain.RESOLVED)
        .select_related("survei__dokter__poliklinik")[:5],
    }, "ringkasan")


# ---------- B. Peringkat dokter ----------

@staff_required
def peringkat(request):
    periode = _periode(request, "semua")
    poli_id = _angka(request.GET.get("poli"))
    cari = request.GET.get("q", "").strip()
    daftar = services.leaderboard(poli_id=poli_id, sejak=services.mulai_periode(periode), cari=cari)
    return tampil(request, "dashboard/peringkat.html", {
        "daftar": daftar,
        "periode": periode,
        "daftar_periode": services.PERIODE,
        "poli_id": poli_id,
        "daftar_poli": Poliklinik.objects.all(),
        "cari": cari,
    }, "peringkat")


# ---------- C. Red Alert ----------

@staff_required
def komplain_list(request):
    status = request.GET.get("status", "")
    hitung = {r["status"]: r["n"] for r in Komplain.objects.values("status").annotate(n=Count("id"))}
    qs = Komplain.objects.select_related("survei__dokter__poliklinik")
    if status in dict(Komplain.STATUS):
        qs = qs.filter(status=status)
    return tampil(request, "dashboard/komplain_list.html", {
        "daftar": qs,
        "status": status,
        "tab_status": [(k, label, hitung.get(k, 0)) for k, label in Komplain.STATUS],
        "total": sum(hitung.values()),
    }, "komplain")


@staff_required
def komplain_detail(request, pk):
    k = get_object_or_404(Komplain.objects.select_related("survei__dokter__poliklinik"), pk=pk)
    if request.method == "POST":
        status = request.POST.get("status", "")
        catatan = request.POST.get("catatan", "").strip()
        if status in dict(Komplain.STATUS):
            k.status = status
        if catatan:
            waktu = timezone.localtime().strftime("%Y-%m-%d %H:%M")
            nama = request.user.get_full_name() or request.user.username
            baris = f"[{waktu} - {nama}] {catatan}"
            k.catatan_tindak_lanjut = f"{k.catatan_tindak_lanjut}\n{baris}" if k.catatan_tindak_lanjut else baris
        k.save()
        messages.success(request, "Komplain diperbarui.")
        return redirect("dashboard:komplain_detail", pk=k.pk)

    jawaban = k.survei.jawaban.select_related("pertanyaan", "opsi")
    return tampil(request, "dashboard/komplain_detail.html", {
        "k": k, "jawaban": jawaban, "daftar_status": Komplain.STATUS,
    }, "komplain")


# ---------- D. Data master ----------

@staff_required
def dokter_list(request):
    poli_id = _angka(request.GET.get("poli"))
    cari = request.GET.get("q", "").strip()
    qs = Dokter.objects.select_related("poliklinik").annotate(jumlah=Count("survei"))
    if poli_id:
        qs = qs.filter(poliklinik_id=poli_id)
    if cari:
        qs = qs.filter(nama__icontains=cari)
    return tampil(request, "dashboard/dokter_list.html", {
        "daftar": qs, "poli_id": poli_id, "cari": cari, "daftar_poli": Poliklinik.objects.all(),
    }, "dokter")


@staff_required
def dokter_form(request, pk=None):
    objek = get_object_or_404(Dokter, pk=pk) if pk else None
    form = DokterForm(request.POST or None, request.FILES or None, instance=objek)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Data dokter disimpan.")
        return redirect("dashboard:dokter")
    return tampil(request, "dashboard/form_umum.html", {
        "form": form,
        "judul": "Ubah dokter" if objek else "Tambah dokter",
        "kembali": reverse("dashboard:dokter"),
        "hapus": reverse("dashboard:dokter_hapus", args=[objek.pk]) if objek else None,
    }, "dokter")


@staff_required
@require_POST
def dokter_hapus(request, pk):
    objek = get_object_or_404(Dokter, pk=pk)
    return _hapus(request, objek, "dashboard:dokter", f"Dokter {objek.nama}")


@staff_required
def poli_list(request):
    qs = Poliklinik.objects.annotate(
        jumlah_dokter=Count("dokter", distinct=True),
        jumlah_soal=Count("pertanyaan", filter=Q(pertanyaan__aktif=True), distinct=True),
    )
    return tampil(request, "dashboard/poli_list.html", {"daftar": qs}, "poli")


@staff_required
def poli_form(request, pk=None):
    objek = get_object_or_404(Poliklinik, pk=pk) if pk else None
    form = PoliForm(request.POST or None, instance=objek)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Poliklinik disimpan.")
        return redirect("dashboard:poli")
    return tampil(request, "dashboard/form_umum.html", {
        "form": form,
        "judul": "Ubah poliklinik" if objek else "Tambah poliklinik",
        "kembali": reverse("dashboard:poli"),
        "hapus": reverse("dashboard:poli_hapus", args=[objek.pk]) if objek else None,
    }, "poli")


@staff_required
@require_POST
def poli_hapus(request, pk):
    objek = get_object_or_404(Poliklinik, pk=pk)
    return _hapus(request, objek, "dashboard:poli", f"Poliklinik {objek.nama}")


@staff_required
def pertanyaan_list(request):
    poli_id = _angka(request.GET.get("poli"))
    qs = Pertanyaan.objects.select_related("poliklinik").prefetch_related("opsi")
    if poli_id:
        qs = qs.filter(poliklinik_id=poli_id)
    return tampil(request, "dashboard/pertanyaan_list.html", {
        "daftar": qs, "poli_id": poli_id, "daftar_poli": Poliklinik.objects.all(),
    }, "pertanyaan")


@staff_required
def pertanyaan_form(request, pk=None):
    objek = get_object_or_404(Pertanyaan, pk=pk) if pk else None
    awal = {}
    if objek is None:
        poli_id = _angka(request.GET.get("poli"))
        if poli_id:
            awal = {"poliklinik": poli_id, "urutan": Pertanyaan.objects.filter(poliklinik_id=poli_id).count() + 1}
    form = PertanyaanForm(request.POST or None, instance=objek, initial=awal)
    formset = OpsiFormSet(request.POST or None, instance=objek)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                tersimpan = form.save()
                formset.instance = tersimpan
                formset.save()
        except ProtectedError:
            messages.error(
                request,
                "Opsi yang sudah dipakai jawaban pasien tidak bisa dihapus. "
                "Ubah label atau bobotnya saja.",
            )
        else:
            messages.success(request, "Pertanyaan disimpan.")
            return redirect("dashboard:pertanyaan")

    return tampil(request, "dashboard/pertanyaan_form.html", {
        "form": form,
        "formset": formset,
        "objek": objek,
    }, "pertanyaan")


@staff_required
@require_POST
def pertanyaan_hapus(request, pk):
    objek = get_object_or_404(Pertanyaan, pk=pk)
    return _hapus(request, objek, "dashboard:pertanyaan", "Pertanyaan")


# ---------- E. QR Code Center ----------

def _url_survei(request):
    url = request.GET.get("url", "").strip()
    return url or settings.SURVEY_BASE_URL


def _url_valid(url):
    return url.startswith(("http://", "https://")) and len(url) <= 500


@staff_required
def qr_center(request):
    url = _url_survei(request)
    return tampil(request, "dashboard/qr.html", {
        "url": url,
        "url_valid": _url_valid(url),
        "alamat_lokal": any(k in url for k in ("localhost", "127.0.0.1")),
    }, "qr")


@staff_required
def qr_gambar(request):
    url = _url_survei(request)
    if not _url_valid(url):
        return HttpResponseBadRequest("Alamat harus diawali http:// atau https://")
    return HttpResponse(reports.buat_qr_png(url), content_type="image/png")


@staff_required
def qr_unduh(request):
    url = _url_survei(request)
    if not _url_valid(url):
        return HttpResponseBadRequest("Alamat harus diawali http:// atau https://")
    if request.GET.get("format") == "pdf":
        isi, tipe, nama = reports.buat_qr_pdf(url), "application/pdf", "qr_survei_rs.pdf"
    else:
        isi, tipe, nama = reports.buat_qr_png(url), "image/png", "qr_survei_rs.png"
    respons = HttpResponse(isi, content_type=tipe)
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


# ---------- F. Laporan & akun ----------

@staff_required
def laporan(request):
    periode = _periode(request, "semua")
    sejak = services.mulai_periode(periode)
    return tampil(request, "dashboard/laporan.html", {
        "periode": periode,
        "daftar_periode": services.PERIODE,
        "label_periode": dict(services.PERIODE)[periode],
        "data": services.ringkasan(sejak),
    }, "laporan")


@staff_required
def laporan_xlsx(request):
    periode = _periode(request, "semua")
    respons = HttpResponse(
        reports.buat_xlsx(periode),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    respons["Content-Disposition"] = f'attachment; filename="laporan_survei_{timezone.localdate()}.xlsx"'
    return respons


@staff_required
def laporan_pdf(request):
    periode = _periode(request, "semua")
    respons = HttpResponse(reports.buat_pdf(periode), content_type="application/pdf")
    respons["Content-Disposition"] = f'attachment; filename="laporan_survei_{timezone.localdate()}.pdf"'
    return respons


@staff_required
def akun_list(request):
    return tampil(request, "dashboard/akun_list.html", {
        "daftar": User.objects.filter(is_staff=True).order_by("username"),
    }, "akun")


@staff_required
def akun_baru(request):
    form = AkunBaruForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Akun admin dibuat.")
        return redirect("dashboard:akun")
    return tampil(request, "dashboard/form_umum.html", {
        "form": form, "judul": "Tambah akun admin", "kembali": reverse("dashboard:akun"), "hapus": None,
    }, "akun")


@staff_required
@require_POST
def akun_toggle(request, pk):
    akun = get_object_or_404(User, pk=pk, is_staff=True)
    if akun.pk == request.user.pk:
        messages.error(request, "Anda tidak bisa menonaktifkan akun yang sedang dipakai.")
    else:
        akun.is_active = not akun.is_active
        akun.save(update_fields=["is_active"])
        messages.success(request, f"Akun {akun.username} {'diaktifkan' if akun.is_active else 'dinonaktifkan'}.")
    return redirect("dashboard:akun")


@staff_required
def akun_password(request, pk):
    akun = get_object_or_404(User, pk=pk, is_staff=True)
    form = SetPasswordForm(akun, request.POST or None)
    form.fields["new_password1"].label = "Kata sandi baru"
    form.fields["new_password1"].help_text = "Minimal 8 karakter dan jangan terlalu mudah ditebak."
    form.fields["new_password2"].label = "Ulangi kata sandi baru"
    form.fields["new_password2"].help_text = ""
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Kata sandi {akun.username} diganti.")
        return redirect("dashboard:akun")
    return tampil(request, "dashboard/form_umum.html", {
        "form": form, "judul": f"Ganti kata sandi: {akun.username}",
        "kembali": reverse("dashboard:akun"), "hapus": None,
    }, "akun")
