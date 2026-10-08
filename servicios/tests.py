import os
import shutil
import tempfile
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from catalogo.models import Promocion
from .forms import ServiciosForm
from .models import Servicios, Calificacion

TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ChichaBarberModelsTestCase(TestCase):

    def setUp(self):
        """Configuración inicial para las pruebas."""
        # Creamos una imagen falsa en memoria para probar las subidas
        self.imagen_falsa = SimpleUploadedFile(
            name='mi_foto_original.jpg', 
            content=b'\x47\x49\x46\x38\x39\x61', 
            content_type='image/jpeg'
        )
        
        # Servicio base para usar en las pruebas con ForeingKey
        self.servicio = Servicios.objects.create(
            nombre="Corte Fade Clásico",
            precio=15000.00,
            duracion=30,
            descripcion="El degradado perfecto para la barbería."
        )

    def test_creacion_servicio_y_renombrado_imagen(self):
        """Verifica que un servicio se guarde correctamente y renombre su imagen usando su PK."""
        servicio_con_foto = Servicios.objects.create(
            nombre="Corte de Cabello Premium",
            precio=25000.00,
            duracion=45,
            descripcion="Corte con lavado y masaje.",
            imagen=self.imagen_falsa
        )
        
        # Comprobamos que el método __str__ funcione
        self.assertEqual(str(servicio_con_foto), "Corte de Cabello Premium")
        
        # Validamos que el método save() haya estructurado y renombrado la imagen como querías:
        # "servicios/corte-de-cabello-premium_<pk>.jpg"
        nombre_esperado = f"servicios/corte-de-cabello-premium_{servicio_con_foto.pk}.jpg"
        self.assertEqual(servicio_con_foto.imagen.name, nombre_esperado)

    def test_creacion_promocion_y_renombrado_imagen(self):
        """Verifica la correcta asignación de promociones y el slugify de su imagen."""
        promocion = Promocion.objects.create(
            nombre="Combo Descuento Papá",
            porcentaje_descuento=15.50,
            descripcion="Trae a tu hijo y recibe descuento.",
            fecha_inicio=timezone.now().date(),
            fecha_fin=timezone.now().date(),
            imagen=self.imagen_falsa,
            codigo_servicio=self.servicio,
        )
        
        self.assertEqual(str(promocion), "Combo Descuento Papá")
        
        # Promocion conserva el nombre original del archivo dentro de promociones/.
        nombre_esperado = "promociones/mi_foto_original.jpg"
        self.assertEqual(promocion.imagen.name, nombre_esperado)

    def test_calificacion_y_ordenamiento(self):
        """Prueba que las calificaciones se vinculen al servicio y respeten el orden invertido."""
        # Creamos dos calificaciones con tiempos sutilmente distintos
        calificacion_antigua = Calificacion.objects.create(
            servicio=self.servicio,
            cliente_nombre="Juan Pérez",
            puntuacion=5,
            comentario="¡El mejor degradado del barrio!"
        )
        
        calificacion_reciente = Calificacion.objects.create(
            servicio=self.servicio,
            cliente_nombre="Andrés Mendoza",
            puntuacion=4,
            comentario="Muy buen servicio, demoró un poco."
        )
        
        # Comprobamos el método __str__
        self.assertEqual(
            str(calificacion_antigua), 
            "Juan Pérez - Corte Fade Clásico (5 estrellas)"
        )
        
        # Comprobamos el ordenamiento ['-fecha_calificacion'] 
        # La más reciente debe aparecer primero en la lista
        primer_elemento = Calificacion.objects.all().first()
        self.assertEqual(primer_elemento, calificacion_reciente)

    def tearDown(self):
        """Limpieza de archivos huérfanos creados durante los tests."""
        # Evita que se llene tu carpeta media/ de archivos basura generados por las pruebas
        for servicio in Servicios.objects.all():
            if servicio.imagen:
                if os.path.exists(servicio.imagen.path):
                    os.remove(servicio.imagen.path)
                    
        for promo in Promocion.objects.all():
            if promo.imagen:
                if os.path.exists(promo.imagen.path):
                    os.remove(promo.imagen.path)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


class ServiciosFormValidationTests(SimpleTestCase):
    def setUp(self):
        self.valid_data = {
            'nombre': 'Corte Fade 2',
            'precio': '25000.00',
            'duracion': '30',
            'descripcion': 'Corte clásico con acabado profesional.',
        }

    def test_accepts_valid_service_data_with_spanish_characters(self):
        self.valid_data['nombre'] = 'Corte Clásico 2'
        form = ServiciosForm(data=self.valid_data)

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_markup_in_service_name(self):
        self.valid_data['nombre'] = '<script>alert(1)</script>'
        form = ServiciosForm(data=self.valid_data)

        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_rejects_negative_price(self):
        self.valid_data['precio'] = '-1'
        form = ServiciosForm(data=self.valid_data)

        self.assertFalse(form.is_valid())
        self.assertIn('precio', form.errors)

    def test_rejects_zero_duration(self):
        self.valid_data['duracion'] = '0'
        form = ServiciosForm(data=self.valid_data)

        self.assertFalse(form.is_valid())
        self.assertIn('duracion', form.errors)

    def test_requires_description_when_creating_service(self):
        self.valid_data.pop('descripcion')
        form = ServiciosForm(data=self.valid_data)

        self.assertFalse(form.is_valid())
        self.assertIn('descripcion', form.errors)


# Create your tests here.
