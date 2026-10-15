from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Usuario, Notificacion
from servicios.models import Servicios
from reservas.models import Agenda, Reserva


class ReservaBookingFlowTest(TestCase):
    def setUp(self):
        self.client_user = Usuario.objects.create(
            email="cliente-flujo@gmail.com",
            numero_documento="980000101",
            telefono="3000000101",
            primer_nombre="Cliente",
            primer_apellido="Flujo",
            rol="cliente",
        )
        self.admin_user = Usuario.objects.create(
            email="admin-flujo@gmail.com",
            numero_documento="980000103",
            telefono="3000000103",
            primer_nombre="Admin",
            primer_apellido="Flujo",
            rol="admin",
        )
        self.barbero = Usuario.objects.create(
            email="barbero-flujo@example.com",
            numero_documento="980000102",
            telefono="3000000102",
            primer_nombre="Barbero",
            primer_apellido="Flujo",
            rol="barbero",
        )
        self.servicio = Servicios.objects.create(
            nombre="Corte flujo",
            precio=Decimal("25000.00"),
            duracion=30,
            descripcion="Servicio para probar el flujo de reserva",
        )
        self.agenda = Agenda.objects.create(
            profesional=self.barbero,
            fecha=timezone.localdate() + timedelta(days=2),
            hora_inicio=time(10, 0),
            hora_fin=time(10, 30),
        )
        self.url = reverse("crear_reserva", args=[self.servicio.pk])
        self.datos_reserva = {
            "barbero_id": str(self.barbero.pk),
            "turno_id": str(self.agenda.pk),
            "nombre_cliente": "Cliente Flujo",
            "correo_cliente": self.client_user.email,
            "telefono_cliente": "3000000101",
            "medio_pago": "transferencia",
        }

    def test_cliente_puede_confirmar_reserva_y_guardar_medio_pago(self):
        self.client.force_login(self.client_user)

        with patch("reservas.views.enviar_correo_reserva"):
            response = self.client.post(self.url, self.datos_reserva)

        self.assertEqual(response.status_code, 302)
        reserva = Reserva.objects.get(agenda=self.agenda)
        self.assertEqual(reserva.usuario, self.client_user)
        self.assertEqual(reserva.nombre_usuario, "Cliente Flujo")
        self.assertEqual(reserva.correo_usuario, self.client_user.email)
        self.assertEqual(reserva.medio_pago, "transferencia")
        self.assertEqual(
            Agenda.objects.get(pk=self.agenda.pk).estado,
            "reservada",
        )
        self.assertEqual(
            response.url,
            reverse("reserva_confirmada", args=[reserva.pk]),
        )

    def test_cliente_no_puede_reservar_turno_pasado(self):
        self.agenda.fecha = timezone.localdate() - timedelta(days=1)
        self.agenda.save(update_fields=["fecha"])
        self.client.force_login(self.client_user)

        response = self.client.post(self.url, self.datos_reserva)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El turno seleccionado no está disponible")
        self.assertFalse(Reserva.objects.filter(agenda=self.agenda).exists())
        self.assertEqual(Agenda.objects.get(pk=self.agenda.pk).estado, "disponible")

    def test_cliente_no_autenticado_reanuda_la_reserva_despues_de_registrarse(self):
        response = self.client.post(self.url, self.datos_reserva)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("registro"), response.url)
        self.assertEqual(
            self.client.session["reserva_pendiente"]["turno_id"],
            str(self.agenda.pk),
        )

        self.client.force_login(self.client_user)
        with patch("reservas.views.enviar_correo_reserva"):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        reserva = Reserva.objects.get(agenda=self.agenda)
        self.assertEqual(reserva.medio_pago, "transferencia")
        self.assertNotIn("reserva_pendiente", self.client.session)

    def test_api_solo_devuelve_turnos_futuros_disponibles(self):
        self.agenda.fecha = timezone.localdate() - timedelta(days=1)
        self.agenda.save(update_fields=["fecha"])

        response = self.client.get(reverse("api_turnos_disponibles"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["turnos"], [])

    def test_entrada_sin_servicio_lleva_al_catalogo(self):
        response = self.client.get(reverse("crear_reserva_directa"))

        self.assertRedirects(response, reverse("servicios"))

    def test_administrador_puede_crear_cita_con_datos_del_cliente(self):
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("crear_reserva_admin"),
            {
                "nombre_cliente": "Cliente Agendado",
                "correo_cliente": "cliente-agendado@gmail.com",
                "telefono_cliente": "3000000104",
                "servicio": str(self.servicio.pk),
                "turno_id": str(self.agenda.pk),
            },
        )

        self.assertEqual(response.status_code, 302)
        reserva = Reserva.objects.get(agenda=self.agenda)
        self.assertEqual(reserva.nombre_cliente, "Cliente Agendado")
        self.assertEqual(reserva.correo_cliente, "cliente-agendado@gmail.com")
        self.assertEqual(Agenda.objects.get(pk=self.agenda.pk).estado, "reservada")
class AgendaModelTest(TestCase):

    def setUp(self):
        self.barbero = Usuario.objects.create(
            email="barbero1@example.com",
            numero_documento="900000001",
            telefono="3000000001",
            primer_nombre="Juan",
            primer_apellido="Pérez",
            rol="barbero"
        )

    def test_crear_agenda(self):
        agenda = Agenda.objects.create(
            profesional=self.barbero,
            fecha=date.today(),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0),
            estado="disponible"
        )

        self.assertEqual(agenda.profesional, self.barbero)
        self.assertEqual(agenda.estado, "disponible")

    def test_str_agenda(self):
        agenda = Agenda.objects.create(
            profesional=self.barbero,
            fecha=date.today(),
            hora_inicio=time(9, 0),
            hora_fin=time(10, 0)
        )

        texto = str(agenda)

        self.assertIn("Juan", texto)
        self.assertIn("09:00:00", texto)


class ReservaModelTest(TestCase):

    def setUp(self):

        self.barbero = Usuario.objects.create(
            email="barbero@example.com",
            numero_documento="900000002",
            telefono="3000000002",
            primer_nombre="Carlos",
            primer_apellido="Ramírez",
            rol="barbero"
        )

        self.usuario = Usuario.objects.create(
            email="cliente@example.com",
            numero_documento="900000003",
            telefono="3000000003",
            primer_nombre="Pedro",
            primer_apellido="López",
            rol="cliente"
        )

        self.admin = Usuario.objects.create(
            email="admin@example.com",
            numero_documento="900000004",
            telefono="3000000004",
            primer_nombre="Administrador",
            primer_apellido="Sistema",
            rol="admin"
        )

        self.servicio = Servicios.objects.create(
            nombre="Corte clásico",
            precio=Decimal("25000"),
            duracion=30,
            descripcion="Corte clásico de prueba"
        )

        self.agenda = Agenda.objects.create(
            profesional=self.barbero,
            fecha=date.today(),
            hora_inicio=time(10, 0),
            hora_fin=time(11, 0)
        )

    def test_crear_reserva(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio,
            precio_historico=Decimal("25000")
        )

        self.assertEqual(reserva.usuario, self.usuario)
        self.assertEqual(reserva.estado, "reservada")
        self.assertEqual(reserva.servicio, self.servicio)

    def test_fecha_reserva_automatica(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio
        )

        self.assertIsNotNone(reserva.fecha_reserva)

        fecha_esperada = timezone.make_aware(
            timezone.datetime.combine(
                self.agenda.fecha,
                self.agenda.hora_inicio
            )
        )

        self.assertEqual(reserva.fecha_reserva, fecha_esperada)

    def test_str_reserva(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio
        )

        texto = str(reserva)

        self.assertIn("Pedro", texto)
        self.assertIn("Corte clásico", texto)

    def test_notificacion_usuario(self):

        Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio
        )

        self.assertTrue(
            Notificacion.objects.filter(
                usuario=self.usuario,
                tipo="reserva"
            ).exists()
        )

    def test_notificacion_admin(self):

        Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio
        )

        self.assertTrue(
            Notificacion.objects.filter(
                usuario=self.admin,
                tipo="reserva"
            ).exists()
        )

    def test_reserva_sin_usuario_registrado(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            telefono_usuario="3000000000",
            observacion="Cliente Invitado sin cuenta",
            servicio=self.servicio
        )

        self.assertEqual(reserva.observacion, "Cliente Invitado sin cuenta")

    def test_estado_por_defecto(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio
        )

        self.assertEqual(reserva.estado, "reservada")

    def test_precio_historico(self):

        reserva = Reserva.objects.create(
            agenda=self.agenda,
            usuario=self.usuario,
            servicio=self.servicio,
            precio_historico=Decimal("30000")
        )

        self.assertEqual(
            reserva.precio_historico,
            Decimal("30000")
        )