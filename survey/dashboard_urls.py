from django.contrib.auth import views as auth_views
from django.urls import path

from . import dashboard_views as v

app_name = "dashboard"

urlpatterns = [
    path("", v.ringkasan, name="ringkasan"),
    path("masuk/", auth_views.LoginView.as_view(template_name="dashboard/masuk.html"), name="masuk"),
    path("keluar/", auth_views.LogoutView.as_view(next_page="dashboard:masuk"), name="keluar"),
    path("peringkat/", v.peringkat, name="peringkat"),
    path("komplain/", v.komplain_list, name="komplain"),
    path("komplain/<int:pk>/", v.komplain_detail, name="komplain_detail"),
    path("dokter/", v.dokter_list, name="dokter"),
    path("dokter/baru/", v.dokter_form, name="dokter_baru"),
    path("dokter/<int:pk>/", v.dokter_form, name="dokter_ubah"),
    path("dokter/<int:pk>/hapus/", v.dokter_hapus, name="dokter_hapus"),
    path("poli/", v.poli_list, name="poli"),
    path("poli/baru/", v.poli_form, name="poli_baru"),
    path("poli/<int:pk>/", v.poli_form, name="poli_ubah"),
    path("poli/<int:pk>/hapus/", v.poli_hapus, name="poli_hapus"),
    path("pertanyaan/", v.pertanyaan_list, name="pertanyaan"),
    path("pertanyaan/baru/", v.pertanyaan_form, name="pertanyaan_baru"),
    path("pertanyaan/<int:pk>/", v.pertanyaan_form, name="pertanyaan_ubah"),
    path("pertanyaan/<int:pk>/hapus/", v.pertanyaan_hapus, name="pertanyaan_hapus"),
    path("qr/", v.qr_center, name="qr"),
    path("qr/gambar.png", v.qr_gambar, name="qr_gambar"),
    path("qr/unduh/", v.qr_unduh, name="qr_unduh"),
    path("laporan/", v.laporan, name="laporan"),
    path("laporan/xlsx/", v.laporan_xlsx, name="laporan_xlsx"),
    path("laporan/pdf/", v.laporan_pdf, name="laporan_pdf"),
    path("akun/", v.akun_list, name="akun"),
    path("akun/baru/", v.akun_baru, name="akun_baru"),
    path("akun/<int:pk>/aktif/", v.akun_toggle, name="akun_toggle"),
    path("akun/<int:pk>/password/", v.akun_password, name="akun_password"),
]
