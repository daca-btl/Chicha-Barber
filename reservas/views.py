from decimal import Decimal
from datetime import datetime, date, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

import re
import dns.resolver
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from reservas.models import Reserva, Agenda
from reservas.forms import ReservaEditarForm
from servicios.models import Servicios
from catalogo.models import Promocion
from usuarios.models import Usuario, Notificacion, HistorialAccion
from core.utils import enviar_correo_reserva, enviar_correo_cancelacion_admin


# Solo letras (incluye tildes y ñ), espacios, apóstrofes y guiones. Mínimo 3 caracteres.
NOMBRE_REGEX = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'\-\s]{3,100}$")
TELEFONO_REGEX = re.compile(r"^3\d{9}$")

# Dominios de correo muy conocidos: se aceptan sin consultar DNS, para que
# el sistema siga funcionando aunque no haya internet en ese momento.
# Ajusta/agrega aquí el dominio real de tu universidad o empresa si lo necesitas.
DOMINIOS_CONOCIDOS = {
    'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com', 'yahoo.es',
    'icloud.com', 'live.com', 'sena.edu.co',
}


def _dominio_correo_existe(correo):
    """
    Verifica que el dominio del correo tenga un servidor de correo real
    (registro MX). Si el dominio está en DOMINIOS_CONOCIDOS, se acepta
    directamente sin necesitar conexión a internet.

    Para cualquier otro dominio, SÍ requiere poder consultar el DNS.
    Si no se puede consultar (sin internet, timeout, etc.), se RECHAZA
    por seguridad (fail-closed): preferimos bloquear un correo válido
    poco común antes que dejar pasar uno inventado solo porque no
    pudimos verificarlo.
    """
    dominio = correo.split('@')[-1].strip().lower()
    if not dominio:
        return False

    if dominio in DOMINIOS_CONOCIDOS:
        return True

    resolver = dns.resolver.Resolver()
    resolver.timeout = 3
    resolver.lifetime = 3

    try:
        resolver.resolve(dominio, 'MX')
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        # Algunos dominios reciben correo sin un registro MX explícito;
        # como último intento, revisamos si al menos tiene un registro A.
        try:
            resolver.resolve(dominio, 'A')
            return True
        except Exception:
            return False
    except Exception:
        # Sin internet, DNS no disponible, timeout, etc.
        # No podemos verificar -> rechazamos (fail-closed).
        return False


def _validar_datos_contacto(nombre, correo, telefono):
    """
    Valida los datos de contacto en el SERVIDOR, sin confiar en el HTML/JS.
    Devuelve una lista de mensajes de error (vacía si todo está bien).
    """
    errores = []

    # --- Nombre ---
    if not nombre:
        errores.append('El nombre es obligatorio.')
    elif not NOMBRE_REGEX.match(nombre):
        errores.append('El nombre solo puede contener letras y espacios (mínimo 3 caracteres).')

    # --- Correo ---
    if not correo:
        errores.append('El correo electrónico es obligatorio.')
    else:
        try:
            validate_email(correo)
        except ValidationError:
            errores.append('El correo electrónico no tiene un formato válido.')
        else:
            # Solo revisamos el dominio si el formato ya pasó
            if not _dominio_correo_existe(correo):
                errores.append(
                    'No pudimos confirmar que el dominio de este correo exista o '
                    'reciba correos. Usa un correo de un proveedor conocido '
                    '(Gmail, Outlook, Hotmail) o verifica que esté bien escrito.'
                )

    # --- Teléfono ---
    if not telefono:
        errores.append('El teléfono es obligatorio.')
    elif not TELEFONO_REGEX.match(telefono):
        errores.append('El teléfono debe ser un celular colombiano válido: 10 dígitos y empezar por 3.')

    return errores


def _parse_fecha_reserva(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.fromisoformat(fecha_str)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(fecha_str, fmt)
            except ValueError:
                continue
    return None


def obtener_turnos_disponibles_json(request):
    hoy = date.today()
    fin = hoy + timedelta(days=6)
    barbero_id = request.GET.get('barbero_id', 'any')

    agendas = Agenda.objects.filter(
        fecha__range=(hoy, fin),
        estado='disponible'
    ).order_by('fecha', 'hora_inicio')

    if barbero_id and barbero_id != 'any':
        agendas = agendas.filter(profesional_id=barbero_id)

    resultado = [
        {
            'id': agenda.id,
            'barbero_id': agenda.profesional.id,
            'barbero': agenda.profesional.get_full_name(),
            'fecha': agenda.fecha.isoformat(),
            'hora': agenda.hora_inicio.strftime('%H:%M'),
            'imagen': agenda.profesional.foto_perfil.url if agenda.profesional.foto_perfil else None,
        }
        for agenda in agendas
    ]

    return JsonResponse({'turnos': resultado})


def crear_reserva(request, servicio_id=None, promocion_id=None):
    servicio = None
    promo = None
    factura_id = request.GET.get('factura_id') or request.POST.get('factura_id')

    if not request.user.is_authenticated:
        login_url = reverse('login')
        return redirect(f'{login_url}?next={request.get_full_path()}')

    if promocion_id is not None:
        promo = get_object_or_404(Promocion, pk=promocion_id)
        if not promo.codigo_servicio:
            messages.warning(request, 'Esta promoción no está asociada a ningún servicio de reserva.')
            return redirect('promocion')
        servicio = promo.codigo_servicio
    elif servicio_id is not None:
        servicio = get_object_or_404(Servicios, id=servicio_id)
    else:
        messages.warning(request, 'Debe seleccionar un servicio o promoción.')
        return redirect('inicio')

    # Cálculo del precio aplicando descuento si existe promoción
    precio = servicio.precio
    if promo and promo.porcentaje_descuento:
        descuento = Decimal(promo.porcentaje_descuento) / Decimal('100')
        precio = round(precio * (Decimal('1') - descuento), 2)

    # Procesar reserva pendiente guardada en la sesión
    if request.user.is_authenticated and 'reserva_pendiente' in request.session:
        reserva_data = request.session.pop('reserva_pendiente')
        turno_id = reserva_data.get('turno_id')
        telefono = reserva_data.get('telefono_usuario') or reserva_data.get('telefono_cliente')
        nombre = reserva_data.get('nombre_usuario') or reserva_data.get('nombre_cliente') or request.user.get_full_name()
        correo = reserva_data.get('correo_usuario') or reserva_data.get('correo_cliente') or request.user.email
        observacion = reserva_data.get('observacion')

        try:
            agenda_obj = Agenda.objects.get(pk=turno_id, estado='disponible')
            fecha_hora_turno = datetime.combine(agenda_obj.fecha, agenda_obj.hora_inicio)

            reserva = Reserva.objects.create(
                agenda=agenda_obj,
                usuario=request.user,
                nombre_usuario=nombre,
                correo_usuario=correo,
                telefono_usuario=telefono,
                fecha_reserva=fecha_hora_turno,
                observacion=observacion,
                servicio=servicio,
                precio_historico=precio,
            )
            agenda_obj.estado = 'reservada'
            agenda_obj.save()

            try:
                enviar_correo_reserva(
                    correo_cliente=correo,
                    nombre=nombre,
                    servicio=servicio,
                    fecha=fecha_hora_turno,
                )
            except Exception as mail_error:
                print(f"Error al enviar correo de reserva: {mail_error}")

            messages.success(request, '¡Te has registrado con éxito y tu reserva ha sido confirmada!')
            return redirect(reverse('reserva_confirmada', kwargs={'pk': reserva.id}))
        except Agenda.DoesNotExist:
            messages.error(request, 'El turno que habías seleccionado ya no está disponible.')
        except Exception as e:
            messages.error(request, f'Error al procesar tu reserva pendiente: {e}')

    barberos = Usuario.objects.filter(rol='barbero', estado=True)
    ahora = datetime.now()
    hoy = ahora.date()
    fin = hoy + timedelta(days=6)

    turnos_qs = Agenda.objects.filter(
        fecha__range=(hoy, fin),
        estado='disponible'
    ).order_by('fecha', 'hora_inicio')

    turnos_disponibles = [
        t for t in turnos_qs
        if t.fecha > hoy or (t.fecha == hoy and t.hora_inicio > ahora.time())
    ]

    action_url = (
        reverse('crear_reserva_promocion', args=[promo.codigo])
        if promo else
        reverse('crear_reserva', args=[servicio.id])
    )

    if request.method == 'POST':
        turno_id = request.POST.get('turno_id')
        telefono = request.POST.get('telefono_usuario', request.POST.get('telefono_cliente', '')).strip()
        correo = request.POST.get('correo_usuario', request.POST.get('correo_cliente', '')).strip() or request.user.email
        nombre = request.POST.get('nombre_usuario', request.POST.get('nombre_cliente', '')).strip() or request.user.get_full_name()
        observacion = request.POST.get('observacion', '').strip()

        # Valores ya elegidos, para no perderlos si hay que volver a mostrar el formulario
        barbero_id_sel = request.POST.get('barbero_id', 'any')
        medio_pago_sel = request.POST.get('medio_pago', 'presencial')

        context_error = {
            'servicio': servicio,
            'barberos': barberos,
            'turnos_disponibles': turnos_disponibles,
            'action_url': action_url,
            'nombre_usuario_val': nombre,
            'correo_usuario_val': correo,
            'telefono_usuario_val': telefono,
            'barbero_id_val': barbero_id_sel,
            'turno_id_val': turno_id,
            'medio_pago_val': medio_pago_sel,
        }

        if not turno_id:
            context_error['wizard_error_step'] = 1  # Paso "Turno"
            context_error['wizard_errors'] = ['Selecciona un turno disponible.']
            return render(request, 'reservas/reservas.html', context_error)

        # ---- VALIDACIÓN SERVIDOR (aquí está lo importante) ----
        errores = _validar_datos_contacto(nombre, correo, telefono)
        if errores:
            context_error['wizard_error_step'] = 2  # Paso "Datos"
            context_error['wizard_errors'] = errores
            return render(request, 'reservas/reservas.html', context_error)
        # --------------------------------------------------------

        if not request.user.is_authenticated:
            request.session['reserva_pendiente'] = {
                'turno_id': turno_id,
                'telefono_cliente': telefono,
                'correo_cliente': correo,
                'nombre_cliente': nombre,
                'observacion': observacion,
            }
            messages.info(request, 'Por favor, regístrate o inicia sesión para confirmar tu reserva.')
            login_url = reverse('registro')
            return redirect(f'{login_url}?next={request.get_full_path()}')

        try:
            with transaction.atomic():
                agenda_obj = Agenda.objects.select_for_update().get(pk=turno_id, estado='disponible')

                precio = servicio.precio
                fecha_hora_turno = datetime.combine(agenda_obj.fecha, agenda_obj.hora_inicio)

                reserva = Reserva.objects.create(
                    agenda=agenda_obj,
                    usuario=request.user,
                    nombre_usuario=nombre,
                    correo_usuario=correo,
                    telefono_usuario=telefono,
                    fecha_reserva=fecha_hora_turno,
                    observacion=observacion,
                    servicio=servicio,
                    precio_historico=precio,
                )
                agenda_obj.estado = 'reservada'
                agenda_obj.save()

            try:
                enviar_correo_reserva(
                    correo_cliente=correo,
                    nombre=nombre,
                    servicio=servicio,
                    fecha=fecha_hora_turno,
                )
            except Exception as mail_error:
                print(f"Error al enviar correo de reserva: {mail_error}")

            messages.success(request, '¡Tu reserva ha sido confirmada!')
            return redirect(reverse('reserva_confirmada', kwargs={'pk': reserva.id}))
        except Agenda.DoesNotExist:
            reserva_existente = Reserva.objects.filter(agenda_id=turno_id).first()
            if reserva_existente:
                return redirect(reverse('reserva_confirmada', kwargs={'pk': reserva_existente.id}))
            messages.error(request, '¡Ups! El turno seleccionado ya no está disponible. Por favor elige otro.')
        except Exception as e:
            messages.error(request, f'Error al crear la reserva: {e}')

    context = {
        'servicio': servicio,
        'promo': promo,
        'barberos': barberos,
        'turnos_disponibles': turnos_disponibles,
        'action_url': action_url,
        'nombre_usuario_val': request.user.get_full_name() if request.user.is_authenticated else '',
        'correo_usuario_val': request.user.email if request.user.is_authenticated else '',
        'telefono_usuario_val': request.user.telefono if request.user.is_authenticated else '',
    }

    return render(request, 'reservas/reservas.html', context)


def reserva_confirmada(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    context = {'reserva': reserva}
    return render(request, 'reservas/reserva_confirmada.html', context)


@login_required
def cancelar_cita(request, pk):
    cita = get_object_or_404(Reserva, pk=pk)

    cita.estado = "cancelada"
    cita.save()

    if cita.agenda:
        cita.agenda.estado = "disponible"
        cita.agenda.save()

    # Notificación Cliente
    Notificacion.objects.create(
        usuario=request.user,
        reserva=cita,
        servicio=cita.servicio,
        tipo="reserva",
        mensaje=(
            f"Se canceló tu cita del "
            f"{cita.agenda.fecha if cita.agenda else 'día seleccionado'}."
        ),
        url="/perfil/",
    )

    # Registro de Historial
    HistorialAccion.objects.create(
        usuario=request.user,
        reserva=cita,
        servicio=cita.servicio,
        tipo="reserva",
        accion="cancelar",
        descripcion=(
            f"Canceló la reserva "
            f"de {cita.servicio.nombre}."
        ),
    )

    # Notificar Administradores
    admins = Usuario.objects.filter(
        Q(rol="admin") | Q(is_superuser=True)
    ).distinct()

    for admin in admins:
        Notificacion.objects.create(
            usuario=admin,
            reserva=cita,
            servicio=cita.servicio,
            tipo="reserva",
            mensaje=(
                f"{request.user.get_full_name()} canceló una cita."
            ),
            url="/admin-reservas/",
        )

    messages.warning(request, f'Cita cancelada: {cita.nombre_cliente}')
    return redirect('ver_agenda')


@login_required
def editar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    form = ReservaEditarForm(request.POST or None, instance=reserva)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Reserva actualizada.')
        return redirect('ver_agenda')

    context = {
        'form': form,
        'reserva': reserva,
    }
    return render(request, 'reservas/editar_reserva.html', context)


@login_required
def ver_agenda(request):
    if request.user.rol not in ['admin', 'barbero']:
        messages.error(request, "No tienes permiso para ver la agenda.")
        return redirect('inicio')

    hoy_fecha = date.today()
    mes_actual = hoy_fecha.month
    anio_actual = hoy_fecha.year

    total_citas_mes = Reserva.objects.filter(
        agenda__fecha__month=mes_actual,  # <-- Actualizado a agenda
        agenda__fecha__year=anio_actual
    ).exclude(estado='cancelada').count()

    turnos_disponibles_hoy = Agenda.objects.filter(
        fecha=hoy_fecha,
        estado='disponible'
    ).count()

    citas_canceladas_mes = Reserva.objects.filter(
        agenda__fecha__month=mes_actual,
        agenda__fecha__year=anio_actual,
        estado='cancelada'
    ).count()

    lista_reservas = Reserva.objects.select_related('agenda__profesional', 'servicio', 'usuario').all().order_by('-agenda__fecha', '-agenda__hora_inicio')
    turnos_disponibles = Agenda.objects.select_related('profesional').filter(
        estado='disponible'
    ).order_by('fecha', 'hora_inicio')
    servicios = Servicios.objects.all()

    context = {
        'reservas': lista_reservas,
        'turnos_disponibles': turnos_disponibles,
        'servicios': servicios,
        'titulo': 'Agenda de Citas',
        'total_citas_mes': total_citas_mes,
        'turnos_disponibles_hoy': turnos_disponibles_hoy,
        'citas_canceladas_mes': citas_canceladas_mes,
    }
    return render(request, 'reservas/ver_agenda.html', context)


@login_required
def cambiar_estado_reserva(request, pk, nuevo_estado):
    reserva = get_object_or_404(Reserva, pk=pk)
    if nuevo_estado in ['reservada', 'confirmada', 'cancelada']:
        reserva.estado = nuevo_estado
        reserva.save()

        if nuevo_estado == 'cancelada' and reserva.agenda:
            reserva.agenda.estado = 'disponible'
            reserva.agenda.save()

        messages.info(request, f'Estado actualizado a {nuevo_estado}.')
    else:
        messages.error(request, 'Estado inválido.')
    return redirect('ver_agenda')


@login_required
def reprogramar_cita(request, pk):
    cita = get_object_or_404(Reserva, pk=pk)
    form = ReservaEditarForm(request.POST or None, instance=cita)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Cita reprogramada.')
        return redirect('ver_agenda')

    context = {
        'form': form,
        'cita': cita,
    }
    return render(request, 'reservas/reprogramar.html', context)


@login_required
def crear_reserva_admin(request):
    if not (request.user.is_staff or request.user.rol == 'admin'):
        messages.error(request, "Acceso restringido a administradores.")
        return redirect('ver_agenda')

    servicios = Servicios.objects.all()
    barberos = Usuario.objects.filter(rol='barbero', estado=True)

    # Igual que en el wizard de cliente: solo turnos futuros y realmente
    # disponibles. El administrador ELIGE uno de esta lista, no escribe
    # una fecha a mano.
    ahora = datetime.now()
    hoy = ahora.date()
    fin = hoy + timedelta(days=30)

    turnos_qs = Agenda.objects.select_related('profesional').filter(
        fecha__range=(hoy, fin),
        estado='disponible'
    ).order_by('fecha', 'hora_inicio')

    turnos_disponibles = [
        t for t in turnos_qs
        if t.fecha > hoy or (t.fecha == hoy and t.hora_inicio > ahora.time())
    ]

    if request.method == 'POST':
        # Estos "name" deben coincidir EXACTAMENTE con los del formulario
        # (antes leíamos 'telefono_usuario' y nunca llegaba nada porque el
        # input se llama 'telefono_cliente'; nombre y correo ni se leían).
        nombre = request.POST.get('nombre_cliente', '').strip()
        correo = request.POST.get('correo_cliente', '').strip()
        telefono = request.POST.get('telefono_cliente', '').strip()
        observacion = request.POST.get('observacion', '').strip()
        servicio_id = request.POST.get('servicio')
        turno_id = request.POST.get('turno_id')

        context_error = {
            'servicios': servicios,
            'barberos': barberos,
            'turnos_disponibles': turnos_disponibles,
            'nombre_cliente_val': nombre,
            'correo_cliente_val': correo,
            'telefono_cliente_val': telefono,
            'servicio_id_val': servicio_id,
            'turno_id_val': turno_id,
        }

        # ---- VALIDACIÓN SERVIDOR: misma lógica que en la reserva del cliente ----
        errores = _validar_datos_contacto(nombre, correo, telefono)

        if not servicio_id:
            errores.append('Debes seleccionar un servicio.')

        if not turno_id:
            errores.append('Debes seleccionar un turno disponible de la agenda.')

        if errores:
            context_error['wizard_errors'] = errores
            for err in errores:
                messages.error(request, err)
            return render(request, 'reservas/crear_cita_admin.html', context_error)
        # --------------------------------------------------------------------------

        try:
            with transaction.atomic():
                # select_for_update + estado='disponible': si el turno ya fue
                # tomado por otra reserva o no existe, esto lanza DoesNotExist
                # en vez de crear la cita "flotando" sin agenda real.
                agenda_obj = Agenda.objects.select_for_update().get(
                    pk=turno_id,
                    estado='disponible',
                )
                servicio = Servicios.objects.get(id=servicio_id)

                Reserva.objects.create(
                    agenda=agenda_obj,
                    usuario=None,  # es una cita de un cliente, no del admin que la registra
                    nombre_usuario=nombre,
                    correo_usuario=correo,
                    telefono_usuario=telefono,
                    observacion=observacion,
                    servicio=servicio,
                    precio_historico=servicio.precio,
                )
                agenda_obj.estado = 'reservada'
                agenda_obj.save()

            messages.success(request, '¡Cita registrada!')
            return redirect('ver_agenda')

        except Agenda.DoesNotExist:
            messages.error(request, 'El turno seleccionado ya no está disponible. Elige otro de la agenda.')
        except Servicios.DoesNotExist:
            messages.error(request, 'El servicio seleccionado no existe.')
        except Exception as e:
            messages.error(request, f'Error al registrar la cita: {e}')

        context_error['wizard_errors'] = []
        return render(request, 'reservas/crear_cita_admin.html', context_error)

    context = {
        'servicios': servicios,
        'barberos': barberos,
        'turnos_disponibles': turnos_disponibles,
    }
    return render(request, 'reservas/crear_cita_admin.html', context)


@login_required
def gestionar_disponibilidad_dias(request):
    if not (request.user.is_staff or request.user.rol == 'admin'):
        messages.error(request, "No tienes permisos para gestionar la disponibilidad.")
        return redirect('ver_agenda')

    hoy = date.today()
    dias = []

    for i in range(15):
        fecha = hoy + timedelta(days=i)
        turnos_count = Agenda.objects.filter(fecha=fecha, estado='disponible').count()
        reservas_count = Agenda.objects.filter(fecha=fecha, estado='reservada').count()  # <-- Actualizado a 'reservada'

        dias.append({
            'fecha': fecha,
            'disponible': turnos_count > 0,
            'cantidad': turnos_count,
            'reservas': reservas_count,
            'es_hoy': fecha == hoy
        })

    barberos = Usuario.objects.filter(rol='barbero', estado=True)

    context = {
        'dias': dias,
        'barberos': barberos,
        'titulo': 'Gestión de Agenda por Días'
    }
    return render(request, 'reservas/gestion_turno.html', context)


@login_required
def activar_dia_agenda(request, fecha_str):
    if not (request.user.is_staff or request.user.rol == 'admin'):
        messages.error(request, "Acceso denegado.")
        return redirect('ver_agenda')

    if request.method == 'POST':
        fecha = date.fromisoformat(fecha_str)
        barbero_id = request.POST.get('barbero')
        h_inicio_val = int(request.POST.get('hora_inicio', 8))
        h_fin_val = int(request.POST.get('hora_fin', 18))
        duracion = int(request.POST.get('duracion', 60))
        h_almuerzo_inicio = request.POST.get('h_almuerzo_inicio')
        h_almuerzo_fin = request.POST.get('h_almuerzo_fin')

        if barbero_id == 'todos':
            barberos = Usuario.objects.filter(rol='barbero', estado=True)
        else:
            barberos = Usuario.objects.filter(id=barbero_id, rol='barbero', estado=True)

        if not barberos.exists():
            messages.error(request, "No se encontraron barberos seleccionados o activos.")
            return redirect('gestionar_dias')

        turnos_creados = 0
        for barbero in barberos:
            inicio_dt = datetime.combine(fecha, time(hour=h_inicio_val))
            fin_dt = datetime.combine(fecha, time(hour=h_fin_val))

            current = inicio_dt
            while current + timedelta(minutes=duracion) <= fin_dt:
                es_almuerzo = False
                if h_almuerzo_inicio and h_almuerzo_fin:
                    try:
                        l_start = time(hour=int(h_almuerzo_inicio))
                        l_end = time(hour=int(h_almuerzo_fin))
                        if l_start <= current.time() < l_end:
                            es_almuerzo = True
                    except ValueError:
                        pass

                if es_almuerzo:
                    current += timedelta(minutes=duracion)
                    continue

                if not Agenda.objects.filter(profesional=barbero, fecha=fecha, hora_inicio=current.time()).exists():
                    Agenda.objects.create(
                        profesional=barbero,
                        fecha=fecha,
                        hora_inicio=current.time(),
                        hora_fin=(current + timedelta(minutes=duracion)).time(),
                        estado='disponible'
                    )
                    turnos_creados += 1
                current += timedelta(minutes=duracion)

        messages.success(request, f"Día {fecha_str} configurado. Se crearon {turnos_creados} turnos.")
    return redirect('gestionar_dias')


@login_required
def desactivar_dia_agenda(request, fecha_str):
    if not (request.user.is_staff or request.user.rol == 'admin'):
        messages.error(request, "Acceso denegado.")
        return redirect('ver_agenda')

    fecha = date.fromisoformat(fecha_str)

    reservas_afectadas = Reserva.objects.filter(
        agenda__fecha=fecha,  # <-- Actualizado a agenda
        estado__in=['reservada', 'confirmada']
    )

    cantidad_notificada = 0
    for reserva in reservas_afectadas:
        reserva.estado = 'cancelada'
        reserva.save()

        try:
            enviar_correo_cancelacion_admin(
                correo_cliente=reserva.correo_cliente,
                nombre=reserva.nombre_cliente,
                servicio=reserva.servicio.nombre,
                fecha=reserva.fecha_reserva
            )
            cantidad_notificada += 1
        except Exception as e:
            print(f"Error al notificar a {reserva.correo_cliente}: {e}")

    Agenda.objects.filter(fecha=fecha, estado='disponible').delete()

    if cantidad_notificada > 0:
        messages.success(request, f"Se cancelaron {cantidad_notificada} citas y se enviaron los correos de notificación.")

    messages.warning(request, f"Día {fecha_str} desactivado. No se aceptarán más reservas para esta fecha.")

    return redirect('gestionar_dias')