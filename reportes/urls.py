from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReporteDiarioViewSet


router = DefaultRouter()
router.register(
    r"reporte-diario",
    ReporteDiarioViewSet,
    basename="reporte-diario",
)

urlpatterns = [
    path("", include(router.urls)),
]
