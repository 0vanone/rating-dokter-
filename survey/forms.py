from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Dokter, OpsiJawaban, Pertanyaan, Poliklinik


class DokterForm(forms.ModelForm):
    class Meta:
        model = Dokter
        fields = ["nama", "poliklinik", "foto", "aktif"]
        labels = {
            "nama": "Nama dokter (lengkap dengan gelar)",
            "poliklinik": "Poliklinik",
            "foto": "Foto (opsional)",
            "aktif": "Aktif (tampil di pilihan pasien)",
        }
        widgets = {"foto": forms.FileInput(attrs={"accept": "image/*"})}


class PoliForm(forms.ModelForm):
    class Meta:
        model = Poliklinik
        fields = ["nama"]
        labels = {"nama": "Nama poliklinik"}


class PertanyaanForm(forms.ModelForm):
    class Meta:
        model = Pertanyaan
        fields = ["poliklinik", "teks", "urutan", "aktif"]
        labels = {
            "poliklinik": "Muncul di poliklinik",
            "teks": "Teks pertanyaan",
            "urutan": "Urutan tampil",
            "aktif": "Aktif (tampil di survei)",
        }


OpsiFormSet = forms.inlineformset_factory(
    Pertanyaan,
    OpsiJawaban,
    fields=["label", "skor", "urutan"],
    extra=1,
    can_delete=True,
    min_num=2,
    validate_min=True,
)


class AkunBaruForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Username"
        self.fields["username"].help_text = "Dipakai untuk masuk. Huruf, angka, dan . _ - saja."
        self.fields["first_name"].label = "Nama lengkap"
        self.fields["first_name"].required = True
        self.fields["email"].label = "Email (opsional)"
        self.fields["password1"].label = "Kata sandi"
        self.fields["password1"].help_text = "Minimal 8 karakter dan jangan terlalu mudah ditebak."
        self.fields["password2"].label = "Ulangi kata sandi"
        self.fields["password2"].help_text = ""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
        return user
