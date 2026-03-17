"""URL principal do projeto Django."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.controle_auditoria.api.views import DashboardView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="schema",
    ),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
    path("api/v1/", include("apps.controle_auditoria.api.urls")),
]
