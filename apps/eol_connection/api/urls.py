"""URLs do app `eol_connection`."""

from django.urls import path

from apps.eol_connection.api.views import HealthCheckEOLView

urlpatterns = [
    path("eol-healthcheck/", HealthCheckEOLView.as_view(), name="eol-healthcheck"),
]
