from decimal import Decimal
from datetime import datetime, time, timedelta

from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from catalogo.models import Producto
from compra.models import Compra
from historial.models import Bitacora
from reservas.models import Reserva
from servicios.models import Servicios
from usuarios.models import Usuario
from venta.models import Venta


def _dinero(valor):
    return f"{valor or Decimal('0.00'):.2f}"


class ReporteDiarioViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    def list(self, request):
        fecha_parametro = request.query_params.get("fecha")
        try:
            fecha = (
                parse_date(fecha_parametro)
                if fecha_parametro
                else timezone.localdate()
            )
        except ValueError:
            fecha = None
        if fecha is None:
            return Response(
                {"error": "El parámetro 'fecha' debe tener formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inicio = timezone.make_aware(datetime.combine(fecha, time.min))
        fin = timezone.make_aware(
            datetime.combine(fecha + timedelta(days=1), time.min)
        )

        ventas = Venta.objects.filter(
            fecha__gte=inicio,
            fecha__lt=fin,
        ).order_by("-fecha")
        compras = Compra.objects.filter(fecha=fecha).select_related(
            "codigo_proveedor"
        ).order_by("-fecha", "-codigo")
        reservas = Reserva.objects.filter(
            Q(fecha_reserva__gte=inicio, fecha_reserva__lt=fin)
            | Q(
                fecha_reserva__isnull=True,
                fecha_creacion__gte=inicio,
                fecha_creacion__lt=fin,
            )
        ).select_related("usuario", "servicio").order_by(
            "-fecha_reserva", "-fecha_creacion"
        )
        historial = Bitacora.objects.filter(
            fecha__gte=inicio,
            fecha__lt=fin,
        ).select_related("codigo_usuario").order_by("-fecha")

        ventas_completadas = ventas.filter(estado_pago="completado")
        ingresos = ventas_completadas.aggregate(
            total=Sum("total_venta")
        )["total"] or Decimal("0.00")
        gastos = compras.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
        reservas_por_estado = dict(
            reservas.values_list("estado").annotate(total=Count("pk"))
        )

        productos = Producto.objects.select_related(
            "codigo_detalle_producto", "codigo_categoria"
        )
        productos_stock_bajo = productos.filter(
            codigo_detalle_producto__isnull=False,
            codigo_detalle_producto__cantidad_actual__lte=F(
                "codigo_detalle_producto__stock_min"
            ),
        )

        servicios_reservados = (
            reservas.values("servicio__nombre")
            .annotate(cantidad=Count("pk"))
            .order_by("servicio__nombre")
        )

        return Response({
            "fecha": fecha.isoformat(),
            "ventas": {
                "cantidad": ventas.count(),
                "completadas": ventas_completadas.count(),
                "ingresos": _dinero(ingresos),
                "registros": [
                    {
                        "codigo": venta.codigo_venta,
                        "cliente": venta.nombre_cliente,
                        "estado_pago": venta.estado_pago,
                        "metodo_pago": venta.metodo_pago,
                        "total": _dinero(venta.total_venta),
                        "fecha": timezone.localtime(venta.fecha).isoformat(),
                    }
                    for venta in ventas
                ],
            },
            "compras": {
                "cantidad": compras.count(),
                "total": _dinero(gastos),
                "registros": [
                    {
                        "codigo": compra.codigo,
                        "proveedor": compra.codigo_proveedor.nombre,
                        "total": _dinero(compra.total),
                    }
                    for compra in compras
                ],
            },
            "reservas": {
                "cantidad": reservas.count(),
                "por_estado": reservas_por_estado,
                "registros": [
                    {
                        "servicio": reserva.servicio.nombre,
                        "cliente": reserva.nombre_cliente,
                        "estado": reserva.estado,
                        "fecha": (
                            timezone.localtime(reserva.fecha_reserva).isoformat()
                            if reserva.fecha_reserva
                            else None
                        ),
                    }
                    for reserva in reservas
                ],
            },
            "usuarios": {
                "total": Usuario.objects.count(),
                "activos": Usuario.objects.filter(estado=True).count(),
                "nuevos_en_fecha": Usuario.objects.filter(
                    fecha_creacion__gte=inicio,
                    fecha_creacion__lt=fin,
                ).count(),
                "por_rol": dict(
                    Usuario.objects.values_list("rol").annotate(total=Count("pk"))
                ),
            },
            "catalogo": {
                "productos": productos.count(),
                "productos_activos": productos.filter(estado=True).count(),
                "categorias": (
                    productos.values("codigo_categoria")
                    .exclude(codigo_categoria__isnull=True)
                    .distinct()
                    .count()
                ),
                "productos_stock_bajo": productos_stock_bajo.count(),
            },
            "servicios": {
                "total": Servicios.objects.count(),
                "activos": Servicios.objects.filter(estado=True).count(),
                "reservas_en_fecha": list(servicios_reservados),
            },
            "historial": {
                "cantidad": historial.count(),
                "registros": [
                    {
                        "accion": registro.accion,
                        "modulo": registro.modulo,
                        "descripcion": registro.descripcion,
                        "usuario": (
                            registro.codigo_usuario.email
                            if registro.codigo_usuario
                            else None
                        ),
                        "fecha": timezone.localtime(registro.fecha).isoformat(),
                    }
                    for registro in historial
                ],
            },
            "resumen_financiero": {
                "ingresos_ventas_completadas": _dinero(ingresos),
                "egresos_compras": _dinero(gastos),
                "balance": _dinero(ingresos - gastos),
            },
        })
