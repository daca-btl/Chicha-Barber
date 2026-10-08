from django.test import TestCase
from django.utils import timezone
from usuarios.models import Usuario
from configuraciones.models import Carrusel, Configuracion


class CarruselModelTestCase(TestCase):
    """Pruebas QA para el modelo Carrusel y su lógica de negocio."""

    def test_crear_carrusel(self):
        carrusel = Carrusel.objects.create(
            nombre="Banner Principal",
            texto="Bienvenido a Chicha Barber"
        )
        self.assertEqual(str(carrusel), "Banner Principal")
        self.assertTrue(carrusel.estado)
        self.assertEqual(carrusel.texto, "Bienvenido a Chicha Barber")

    def test_limite_maximo_cuatro_carruseles_activos(self):
        """Verifica que el modelo mantenga máximo 4 carruseles activos."""
        for i in range(5):
            Carrusel.objects.create(
                nombre=f"Banner {i + 1}",
                estado=True
            )

        carruseles_activos = Carrusel.objects.filter(estado=True).count()
        self.assertLessEqual(carruseles_activos, 4)


class ConfiguracionModelTestCase(TestCase):
    """Pruebas QA para el modelo Configuracion."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email="admin_conf@example.com",
            numero_documento="777000111",
            primer_nombre="Admin",
            primer_apellido="Conf",
            password="Password123*",
            rol="admin"
        )

    def test_crear_configuracion(self):
        config = Configuracion.objects.create(
            codigo_usuario=self.usuario,
            fecha_realizacion=timezone.now(),
            nombre="Configuración General",
            descripcion="Parámetros del sistema",
            estado=True
        )
        self.assertEqual(str(config), "Configuración General")
        self.assertTrue(config.estado)
        self.assertEqual(config.codigo_usuario, self.usuario)

