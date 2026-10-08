from decimal import Decimal

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from servicios.models import Servicios


# ==========================================================
# 1. CATEGORIA
# ==========================================================
class Categoria(models.Model):
    codigo = models.AutoField(primary_key=True)

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]


# ==========================================================
# 2. PROVEEDOR
# ==========================================================
class Proveedor(models.Model):
    codigo = models.AutoField(primary_key=True)

    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre"
    )

    telefono = models.CharField(
        max_length=20,
        default="",
        verbose_name="Teléfono"
    )

    correo = models.EmailField(
        default="",
        verbose_name="Correo electrónico"
    )

    direccion = models.CharField(
        max_length=200,
        default="",
        verbose_name="Dirección"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre"]


# ==========================================================
# 3. MARCA
# ==========================================================
class Marca(models.Model):
    codigo = models.AutoField(primary_key=True)

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )

    estado = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ["nombre"]


# ==========================================================
# 4. DETALLE PRODUCTO / INVENTARIO
# ==========================================================
class DetalleProducto(models.Model):
    codigo = models.AutoField(primary_key=True)

    cantidad_actual = models.PositiveIntegerField(
        default=0,
        verbose_name="Cantidad Actual"
    )

    stock_min = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock Mínimo"
    )

    stock_max = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock Máximo"
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )

    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )

    @property
    def codigo_producto(self):
        """
        Obtiene el producto asociado mediante la relación
        inversa definida en Producto.
        """
        return self.producto_principal.first()

    def __str__(self):
        producto = self.codigo_producto

        if producto:
            return f"Inventario de {producto.nombre}"

        return f"Detalle de Producto #{self.codigo}"

    class Meta:
        verbose_name = "Detalle de Producto"
        verbose_name_plural = "Detalles de Productos"


# ==========================================================
# 5. PRODUCTO
# ==========================================================
class Producto(models.Model):
    codigo_producto = models.AutoField(primary_key=True)

    codigo = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="Código"
    )

    codigo_detalle_producto = models.ForeignKey(
        DetalleProducto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="producto_principal",
        verbose_name="Detalle de Producto"
    )

    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )

    imagen = models.ImageField(
        upload_to="productos/",
        null=True,
        blank=True,
        verbose_name="Imagen"
    )

    estado = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Precio"
    )

    codigo_categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos",
        verbose_name="Categoría"
    )

    codigo_marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        verbose_name="Marca"
    )

    # ======================================================
    # GENERACION AUTOMATICA DEL CODIGO
    # ======================================================
    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        super().save(*args, **kwargs)

        if not self.codigo:
            self.codigo = f"PROD-{self.pk:05d}"

            super().save(
                update_fields=["codigo"]
            )

    # ======================================================
    # STOCK ACTUAL
    # ======================================================
    @property
    def stock_actual(self):
        if self.codigo_detalle_producto:
            return self.codigo_detalle_producto.cantidad_actual

        return 0

    # ======================================================
    # PRECIO DE VENTA ACTUAL
    # ======================================================
    @property
    def precio_venta_actual(self):
        """
        Obtiene el precio de venta de la adquisición más reciente.

        DetalleCompra pertenece a la app 'compra', pero está
        relacionada mediante related_name='adquisiciones'.

        La fecha pertenece a Compra, no a DetalleCompra.
        Por eso se utiliza:

            codigo_compra__fecha
        """

        adquisicion = (
            self.adquisiciones
            .select_related("codigo_compra")
            .order_by(
                "-codigo_compra__fecha",
                "-codigo"
            )
            .first()
        )

        if adquisicion:
            return adquisicion.precio_venta

        return self.precio

    # ======================================================
    # PRECIO DE COMPRA ACTUAL
    # ======================================================
    @property
    def precio_compra_actual(self):
        """
        Obtiene el precio de compra de la adquisición más reciente.
        """

        adquisicion = (
            self.adquisiciones
            .select_related("codigo_compra")
            .order_by(
                "-codigo_compra__fecha",
                "-codigo"
            )
            .first()
        )

        if adquisicion:
            return adquisicion.precio_compra

        return Decimal("0.00")

    # ======================================================
    # PRECIO DE VENTA
    # ======================================================
    @property
    def precio_venta(self):
        return self.precio_venta_actual

    # ======================================================
    # ESTADISTICAS
    # ======================================================
    @classmethod
    def total_productos(cls):
        return cls.objects.count()

    @classmethod
    def total_activos(cls):
        return cls.objects.filter(
            estado=True
        ).count()

    @classmethod
    def total_inactivos(cls):
        return cls.objects.filter(
            estado=False
        ).count()

    # ======================================================
    # REPRESENTACION
    # ======================================================
    def __str__(self):
        marca_str = (
            f" ({self.codigo_marca.nombre})"
            if self.codigo_marca
            else ""
        )

        return f"{self.codigo} - {self.nombre}{marca_str}"

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]


# ==========================================================
# 6. MOVIMIENTO DE PRODUCTO
# ==========================================================
class MovimientoProducto(models.Model):

    TIPO_MOVIMIENTO = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
    ]

    codigo = models.AutoField(primary_key=True)

    codigo_detalle_producto = models.ForeignKey(
        DetalleProducto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="movimientos",
        verbose_name="Detalle de Producto"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO,
        verbose_name="Tipo de Movimiento"
    )

    cantidad = models.PositiveIntegerField(
        verbose_name="Cantidad"
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )

    observacion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observación"
    )

    @property
    def producto(self):
        if self.codigo_detalle_producto:
            return self.codigo_detalle_producto.codigo_producto

        return None

    @property
    def motivo(self):
        return self.observacion

    def __str__(self):
        producto = self.producto

        nombre_producto = (
            producto.nombre
            if producto
            else "Producto"
        )

        return (
            f"{self.tipo.capitalize()} - "
            f"{nombre_producto} - "
            f"{self.cantidad}"
        )

    class Meta:
        verbose_name = "Movimiento de Producto"
        verbose_name_plural = "Movimientos de Productos"
        ordering = ["-fecha"]


# ==========================================================
# 7. PROMOCION
# ==========================================================
class Promocion(models.Model):

    codigo = models.AutoField(primary_key=True)

    nombre = models.CharField(
        max_length=150,
        verbose_name="Nombre"
    )

    porcentaje_descuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Porcentaje de Descuento"
    )

    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción"
    )

    fecha_inicio = models.DateField(
        verbose_name="Fecha de Inicio"
    )

    fecha_fin = models.DateField(
        verbose_name="Fecha de Fin"
    )

    imagen = models.ImageField(
        upload_to="promociones/",
        null=True,
        blank=True,
        verbose_name="Imagen"
    )

    estado = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    codigo_producto = models.ForeignKey(
        Producto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promociones_directas",
        verbose_name="Producto"
    )

    codigo_servicio = models.ForeignKey(
        Servicios,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promociones_catalogo",
        verbose_name="Servicio"
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        ordering = ["-fecha_inicio"]


# ==========================================================
# 8. SIGNAL - CREAR DETALLE DE PRODUCTO
# ==========================================================
@receiver(post_save, sender=Producto)
def crear_detalle_producto(
    sender,
    instance,
    created,
    **kwargs
):
    """
    Cuando se crea un Producto y todavía no tiene
    DetalleProducto, se crea automáticamente su inventario.
    """

    if created and not instance.codigo_detalle_producto_id:

        detalle_obj = DetalleProducto.objects.create(
            cantidad_actual=0,
            stock_min=0,
            stock_max=0
        )

        Producto.objects.filter(
            pk=instance.pk
        ).update(
            codigo_detalle_producto=detalle_obj
        )

