from django.test import TestCase
from usuarios.models import Usuario
from catalogo.models import DetalleProducto
from historial.models import Bitacora


class BitacoraModelTestCase(TestCase):
    """Pruebas QA para el modelo Bitacora de auditoría."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="auditor@test.com",
            numero_documento="555444333",
            primer_nombre="Carlos",
            primer_apellido="Auditor",
            password="Password123*",
            rol="admin"
        )
        self.detalle_prod = DetalleProducto.objects.create(
            cantidad_actual=25,
            stock_min=5,
            stock_max=100
        )

    def test_crear_bitacora_con_usuario_y_producto(self):
        """Verifica registro de auditoría con usuario, producto y propiedades calculadas."""
        bitacora = Bitacora.objects.create(
            codigo_usuario=self.usuario,
            codigo_detalle_producto=self.detalle_prod,
            accion="Entrada de mercadería",
            modulo="compras",
            descripcion="Ingreso por factura #1234",
            ip_origen="192.168.1.50"
        )

        self.assertIn("auditor@test.com", str(bitacora))
        self.assertEqual(bitacora.tipo_cambio, "entrada")
        self.assertEqual(bitacora.motivo, "Ingreso por factura #1234")
        self.assertEqual(bitacora.observaciones, "Ingreso por factura #1234")
        self.assertIsNotNone(bitacora.hora)

    def test_crear_bitacora_sistema_anonimo_salida(self):
        """Verifica registro sin usuario (sistema) y detección de tipo de cambio salida."""
        bitacora = Bitacora.objects.create(
            codigo_usuario=None,
            accion="Salida por venta directa",
            modulo="ventas",
            descripcion="Descuento automático"
        )

        self.assertIn("Sistema/Anonimo", str(bitacora))
        self.assertEqual(bitacora.tipo_cambio, "salida")

