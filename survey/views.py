from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import services
from .models import Dokter

SESSION_SURVEI = "survei"
SESSION_JAWABAN = "jawaban"
SESSION_SELESAI = "selesai"


def _angka(nilai):
    nilai = (nilai or "").strip()
    return int(nilai) if nilai.isdigit() else None


def step1(request):
    """Langkah 1: identitas pasien dan pilihan dokter."""
    galat = []
    tersimpan = request.session.get(SESSION_SURVEI) or {}
    if request.method == "GET":
        # Pasien baru mulai lagi: buang penanda halaman terima kasih sebelumnya.
        request.session.pop(SESSION_SELESAI, None)

    nilai = {
        "nama_pasien": tersimpan.get("nama_pasien", ""),
        "no_hp": tersimpan.get("no_hp", ""),
        "dokter": tersimpan.get("dokter_id", ""),
    }

    if request.method == "POST":
        nilai = {
            "nama_pasien": request.POST.get("nama_pasien", "").strip(),
            "no_hp": request.POST.get("no_hp", "").strip(),
            "dokter": request.POST.get("dokter", ""),
        }
        if len(nilai["nama_pasien"]) < 2:
            galat.append("Isi nama Anda.")

        dokter = None
        dokter_id = _angka(nilai["dokter"])
        if dokter_id:
            dokter = Dokter.objects.filter(pk=dokter_id, aktif=True).first()
        if dokter is None:
            galat.append("Pilih dokter yang merawat Anda.")

        if not galat:
            if tersimpan.get("dokter_id") != dokter.pk:
                request.session.pop(SESSION_JAWABAN, None)
            request.session[SESSION_SURVEI] = {
                "dokter_id": dokter.pk,
                "nama_pasien": nilai["nama_pasien"][:120],
                "no_hp": nilai["no_hp"][:20],
            }
            return redirect("survey:step2")

    daftar_dokter = Dokter.objects.filter(aktif=True).select_related("poliklinik").order_by(
        "poliklinik__nama", "nama"
    )
    return render(
        request,
        "survey/step1.html",
        {
            "langkah": 1,
            "galat": galat,
            "nilai": nilai,
            "dokter_terpilih": _angka(str(nilai["dokter"])),
            "daftar_dokter": daftar_dokter,
        },
    )


def step2(request):
    """Langkah 2: kuesioner yang pertanyaannya mengikuti poliklinik dokter terpilih."""
    state = request.session.get(SESSION_SURVEI)
    if not state:
        return redirect("survey:step1")

    dokter = get_object_or_404(Dokter.objects.select_related("poliklinik"), pk=state["dokter_id"])
    pertanyaan = list(
        dokter.poliklinik.pertanyaan.filter(aktif=True).prefetch_related("opsi")
    )
    terpilih = request.session.get(SESSION_JAWABAN, {})
    galat = []

    if request.method == "POST" and pertanyaan:
        jawaban = {}
        for p in pertanyaan:
            pilihan = _angka(request.POST.get(f"p{p.id}"))
            if pilihan in {o.id for o in p.opsi.all()}:
                jawaban[str(p.id)] = pilihan
        if len(jawaban) != len(pertanyaan):
            galat.append("Jawab semua pertanyaan sebelum lanjut.")
            terpilih = jawaban
        else:
            request.session[SESSION_JAWABAN] = jawaban
            return redirect("survey:step3")

    for p in pertanyaan:
        p.terpilih = terpilih.get(str(p.id))

    return render(
        request,
        "survey/step2.html",
        {"langkah": 2, "dokter": dokter, "pertanyaan": pertanyaan, "galat": galat},
    )


def step3(request):
    """Langkah 3: saran untuk dokter, lalu kirim."""
    state = request.session.get(SESSION_SURVEI)
    jawaban = request.session.get(SESSION_JAWABAN)
    if not state:
        return redirect("survey:step1")
    if not jawaban:
        return redirect("survey:step2")

    dokter = get_object_or_404(Dokter.objects.select_related("poliklinik"), pk=state["dokter_id"])

    if request.method == "POST":
        saran = request.POST.get("saran", "").strip()[:1000]
        try:
            services.simpan_survei(
                dokter=dokter,
                nama_pasien=state["nama_pasien"],
                no_hp=state["no_hp"],
                tanggal_kunjungan=timezone.localdate(),
                jawaban=jawaban,
                saran=saran,
            )
        except (ObjectDoesNotExist, ValueError):
            messages.error(request, "Pertanyaan berubah saat Anda mengisi. Silakan jawab ulang.")
            request.session.pop(SESSION_JAWABAN, None)
            return redirect("survey:step2")

        request.session.pop(SESSION_SURVEI, None)
        request.session.pop(SESSION_JAWABAN, None)
        request.session[SESSION_SELESAI] = dokter.nama
        return redirect("survey:step4")

    return render(request, "survey/step3.html", {"langkah": 3, "dokter": dokter})


def step4(request):
    """Langkah 4: ucapan terima kasih, lalu kembali otomatis ke awal."""
    # Sengaja tidak di-pop di sini: JavaScript di langkah 3 mengikuti redirect lalu membuka
    # halaman ini lagi, jadi penanda baru dibuang saat pasien memulai survei berikutnya (step1).
    nama_dokter = request.session.get(SESSION_SELESAI)
    if not nama_dokter:
        return redirect("survey:step1")
    return render(request, "survey/step4.html", {"langkah": 4, "nama_dokter": nama_dokter})
