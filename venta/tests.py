from decimal import Decimal
from django.test import TestCase
from usuarios.models import Usuario, Notificacion
from catalogo.models import Categoria, Marca, Producto, DetalleProducto, MovimientoProducto
from venta.models import Venta, DetalleVenta, DetallePagos


class VentaModelTestCase(TestCase):
    """Pruebas QA para Venta, validación de stock, movimiento de salida y notificaciones."""

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            email="admin_venta@test.com",
            numero_documento="888111222",
            primer_nombre="Admin",
            primer_apellido="Venta",
            password="Password123*",
            rol="admin"
        )
        self.cliente = Usuario.objects.create_user(
            email="cliente_venta@test.com",
            numero_documento="888333444",
            primer_nombre="Cliente",
            primer_apellido="Venta",
            password="Password123*",
            rol="cliente"
        )
        self.categoria = Categoria.objects.create(
            nombre="Cuidado de Barba",
            descripcion="Aceites y bálsamos"
        )
        self.marca = Marca.objects.create(
            nombre="BeardPro",
            descripcion="Marca premium"
        )
        self.detalle_prod = DetalleProducto.objects.create(
            cantidad_actual=15,
            stock_min=2,
            stock_max=50
        )
        self.producto = Producto.objects.create(
            codigo_categoria=self.categoria,
            codigo_marca=self.marca,
            codigo_detalle_producto=self.detalle_prod,
            nombre="Óleo para Barba 30ml",
            descripcion="Aceite hidratante de cedro",
            precio=Decimal("30000.00"),
            estado=True
        )

    def test_venta_exitosa_descuenta_stock_y_crea_salida(self):
        """Verifica venta válida, descuento de stock, movimiento y notificaciones."""
        venta = Venta.objects.create(
            codigo_usuario=self.cliente,
            nombre_cliente="Cliente Venta",
            correo=self.cliente.email,
            telefono="3119876543",
            metodo_pago="efectivo",
            estado_pago="completado"
        )
        self.assertIn("Cliente Venta", str(venta))

        detalle = DetalleVenta.objects.create(
            codigo_venta=venta,
            codigo_producto=self.producto,
            cantidad=3,
            valor_descuento=Decimal("5000.00")
        )

        # Subtotal: (3 * 30000) - 5000 = 85000
        self.assertEqual(detalle.subtotal, Decimal("85000.00"))

        # Total venta actualizado
        venta.refresh_from_db()
        self.assertEqual(venta.total_venta, Decimal("85000.00"))

        # Stock descontado: 15 - 3 = 12
        self.detalle_prod.refresh_from_db()
        self.assertEqual(self.detalle_prod.cantidad_actual, 12)

        # Movimiento de salida registrado
        movimiento = detalle.codigo_movimiento_producto
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.tipo, "salida")
        self.assertEqual(movimiento.cantidad, 3)

        # Notificación generada para cliente
        notif_cliente = Notificacion.objects.filter(usuario=self.cliente, tipo="venta").first()
        self.assertIsNotNone(notif_cliente)

    def test_venta_falla_por_stock_insuficiente(self):
        """Rechaza venta cuando la cantidad solicitada supera las existencias."""
        venta = Venta.objects.create(
            nombre_cliente="Comprador Stock Insuficiente",
            metodo_pago="efectivo"
        )

        with self.assertRaises(ValueError):
            DetalleVenta.objects.create(
                codigo_venta=venta,
                codigo_producto=self.producto,
                cantidad=20  # Disponible: 15
            )

    def test_detalle_pagos_relacion(self):
        """Verifica la vinculación correcta de información bancaria al pago."""
        venta = Venta.objects.create(
            nombre_cliente="Comprador Bancario",
            metodo_pago="transferencia"
        )
        pago = DetallePagos.objects.create(
            codigo_venta=venta,
            banco="Bancolombia",
            tipo_cuenta="Ahorros",
            numero_cuenta="123456789",
            titular="Barbería SAS"
        )
        self.assertIn("Bancolombia", str(pago))
        self.assertEqual(venta.detalle_pago.banco, "Bancolombia")

