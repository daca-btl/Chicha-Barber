from django.test import TestCase

from datetime import date, time
from decimal import Decimal

from django.utils import timezone

from usuarios.models import Usuario, Notificacion
from servicios.models import Servicios
from reservas.models import Agenda, Reserva
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