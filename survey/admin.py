from django.contrib import admin

from .models import Dokter, Jawaban, Komplain, OpsiJawaban, Pertanyaan, Poliklinik, Survei


@admin.register(Poliklinik)
class PoliklinikAdmin(admin.ModelAdmin):
    search_fields = ["nama"]


@admin.register(Dokter)
class DokterAdmin(admin.ModelAdmin):
    list_display = ["nama", "poliklinik", "aktif"]
    list_filter = ["poliklinik", "aktif"]
    search_fields = ["nama"]


class OpsiInline(admin.TabularInline):
    model = OpsiJawaban
    extra = 3


@admin.register(Pertanyaan)
class PertanyaanAdmin(admin.ModelAdmin):
    list_display = ["teks", "poliklinik", "urutan", "aktif"]
    list_filter = ["poliklinik", "aktif"]
    inlines = [OpsiInline]


class JawabanInline(admin.TabularInline):
    model = Jawaban
    extra = 0
    can_delete = False
    readonly_fields = ["pertanyaan", "opsi", "skor"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Survei)
class SurveiAdmin(admin.ModelAdmin):
    list_display = ["dokter", "nama_pasien", "skor_rata", "dibuat"]
    list_filter = ["dokter__poliklinik"]
    search_fields = ["nama_pasien", "dokter__nama"]
    readonly_fields = ["dibuat", "skor_rata"]
    inlines = [JawabanInline]


@admin.register(Komplain)
class KomplainAdmin(admin.ModelAdmin):
    list_display = ["id", "survei", "status", "dibuat"]
    list_filter = ["status"]
