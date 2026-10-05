"""URL principal do projeto Django."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.controle_auditoria.api.views import DashboardView, KanbanView

_API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/kanban/", KanbanView.as_view(), name="kanban"),
    path(
        f"{_API_V1}schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="schema",
    ),
    path(
        f"{_API_V1}docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
    path(_API_V1, include("apps.controle_auditoria.api.urls")),
    path(_API_V1, include("apps.eol_connection.api.urls")),
    path(_API_V1, include("apps.institucional.api.urls")),
    path(_API_V1, include("apps.professores.api.urls")),
    path(_API_V1, include("apps.programas.api.urls")),
]
