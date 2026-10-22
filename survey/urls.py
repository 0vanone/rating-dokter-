from django.urls import path

from . import views

app_name = "survey"

urlpatterns = [
    path("", views.step1, name="step1"),
    path("kuesioner/", views.step2, name="step2"),
    path("saran/", views.step3, name="step3"),
    path("selesai/", views.step4, name="step4"),
]
