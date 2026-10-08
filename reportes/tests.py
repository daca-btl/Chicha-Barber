from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from catalogo.models import DetalleProducto, Producto, Proveedor
from compra.models import Compra
from historial.models import Bitacora
from reservas.models import Reserva
from servicios.models import Servicios
from usuarios.models import Usuario
from venta.models import Venta


class ReporteDiarioAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = Usuario.objects.create(
            email="admin-reportes@example.com",
            numero_documento="980000001",
            telefono="3000000001",
            primer_nombre="Admin",
            primer_apellido="Reportes",
            rol="admin",
        )

    def test_reporte_diario_incluye_resumenes_y_datos_del_dia(self):
        hoy = timezone.localdate()
        Venta.objects.create(
            nombre_cliente="Cliente de prueba",
            total_venta=Decimal("25000.00"),
            estado_pago="completado",
        )
        Venta.objects.create(
            nombre_cliente="Pago pendiente",
            total_venta=Decimal("5000.00"),
            estado_pago="pendiente",
        )
        proveedor = Proveedor.objects.create(nombre="Proveedor de prueba")
        Compra.objects.create(
            codigo_proveedor=proveedor,
            total=Decimal("8000.00"),
        )
        detalle_producto = DetalleProducto.objects.create(
            cantidad_actual=0,
            stock_min=1,
        )
        Producto.objects.create(
            nombre="Producto de prueba",
            codigo_detalle_producto=detalle_producto,
        )
        servicio = Servicios.objects.create(
            nombre="Corte de prueba",
            precio=Decimal("25000.00"),
            duracion=30,
            descripcion="Servicio para probar reportes",
        )
        Reserva.objects.create(
            servicio=servicio,
            nombre_usuario="Cliente de reserva",
            fecha_reserva=timezone.make_aware(
                datetime.combine(hoy, time.min)
            ),
        )
        Bitacora.objects.create(
            codigo_usuario=self.admin,
            accion="Prueba de reporte",
            modulo="reportes",
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/reporte-diario/")

        self.assertEqual(response.status_code, 200)
        reporte = response.json()
        self.assertEqual(reporte["fecha"], hoy.isoformat())
        self.assertEqual(reporte["ventas"]["cantidad"], 2)
        self.assertEqual(reporte["ventas"]["completadas"], 1)
        self.assertEqual(reporte["ventas"]["ingresos"], "25000.00")
        self.assertEqual(reporte["compras"]["cantidad"], 1)
        self.assertEqual(reporte["compras"]["total"], "8000.00")
        self.assertEqual(reporte["reservas"]["cantidad"], 1)
        self.assertEqual(reporte["usuarios"]["total"], 1)
        self.assertEqual(reporte["usuarios"]["nuevos_en_fecha"], 1)
        self.assertEqual(reporte["catalogo"]["productos_stock_bajo"], 1)
        self.assertEqual(reporte["servicios"]["activos"], 1)
        self.assertEqual(reporte["historial"]["cantidad"], 1)
        self.assertEqual(
            reporte["resumen_financiero"]["balance"],
            "17000.00",
        )

    def test_reporte_requiere_usuario_administrador(self):
        usuario = Usuario.objects.create(
            email="cliente-reportes@example.com",
            numero_documento="980000002",
            telefono="3000000002",
            primer_nombre="Cliente",
            primer_apellido="Reportes",
            rol="cliente",
        )
        self.client.force_authenticate(user=usuario)

        response = self.client.get("/api/reporte-diario/")

        self.assertEqual(response.status_code, 403)

    def test_fecha_con_formato_invalido_devuelve_error(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/api/reporte-diario/?fecha=ayer")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_fecha_filtra_las_ventas(self):
        venta = Venta.objects.create(
            nombre_cliente="Venta fuera de fecha",
            total_venta=Decimal("10000.00"),
        )
        venta.fecha = timezone.make_aware(
            datetime(2020, 1, 1)
        )
        venta.save(update_fields=["fecha"])
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            "/api/reporte-diario/",
            {"fecha": date(2020, 1, 1).isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ventas"]["cantidad"], 1)

    def test_dashboard_muestra_enlace_al_reporte_para_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("inicio_admin"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("reporte-diario-list")}"',
        )
        self.assertContains(response, "Generar reporte")
