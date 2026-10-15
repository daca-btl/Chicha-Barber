from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReporteDiarioViewSet,ReportePagina


router = DefaultRouter()
router.register(
    r"reporte-diario",
    ReporteDiarioViewSet,
    basename="reporte-diario",
)

urlpatterns = [
    path(
        "reportes/",
        ReporteDiarioViewSet.as_view({"get": "list"}),
        name="api-reporte-diario",
    ),
    path("pagina/", ReportePagina.as_view(), name="reporte-pagina"),

    path("", include(router.urls)),
]
