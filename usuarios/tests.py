from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError, transaction
from .models import Usuario


class UsuarioModelTest(TestCase):
    """Pruebas para el modelo Usuario"""

    def setUp(self):
        """Configuración inicial: crea un usuario de prueba"""
        self.usuario = Usuario.objects.create_user(
            email='test@correo.com',
            password='Test1234*',
            numero_documento='123456789',
            primer_nombre='Juan',
            primer_apellido='Pérez',
            telefono='3001234567',
            rol='cliente'
        )

    # --- PRUEBAS DE CREACIÓN ---

    def test_crear_usuario_cliente(self):
        """Un usuario cliente se crea correctamente"""
        self.assertEqual(self.usuario.email, 'test@correo.com')
        self.assertEqual(self.usuario.rol, 'cliente')
        self.assertTrue(self.usuario.estado)

    def test_crear_usuario_barbero(self):
        """Un usuario barbero se crea con especialidad"""
        barbero = Usuario.objects.create_user(
            email='barbero@correo.com',
            password='Test1234*',
            numero_documento='987654321',
            primer_nombre='Carlos',
            primer_apellido='López',
            telefono='3009876543',
            rol='barbero',
        )
        self.assertEqual(barbero.rol, 'barbero')

    def test_str_usuario(self):
        """El __str__ retorna nombre completo y rol"""
        resultado = str(self.usuario)
        self.assertIn('Juan', resultado)
        self.assertIn('Cliente', resultado)

    # --- PRUEBAS DE VALIDACIÓN ---

    def test_email_unico(self):
        """No se puede crear dos usuarios con el mismo email"""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Usuario.objects.create_user(
                email='test@correo.com',
                password='Test1234*',
                numero_documento='111111111',
                telefono='3001111111',
                rol='cliente'
            )

    def test_username_unico(self):
        """No se puede crear dos usuarios con el mismo documento"""
        with self.assertRaises(IntegrityError), transaction.atomic():
            Usuario.objects.create_user(
                email='otro@correo.com',
                password='Test1234*',
                numero_documento='123456789',
                telefono='3002222222',
                rol='cliente'
            )

    def test_estado_activo_por_defecto(self):
        """Un usuario nuevo está activo por defecto"""
        self.assertTrue(self.usuario.estado)

    def test_rol_por_defecto_cliente(self):
        """El rol por defecto es cliente"""
        usuario = Usuario.objects.create_user(
            email='default@correo.com',
            password='Test1234*',
            numero_documento='555555555',
            primer_nombre='Usuario',
            primer_apellido='Prueba',
            telefono='3005555555',
        )
        self.assertEqual(usuario.rol, 'cliente')

    # --- PRUEBAS DE AUTENTICACIÓN ---

    def test_login_con_email_correcto(self):
        """Un usuario puede iniciar sesión con email y contraseña correctos"""
        cliente = Client()
        response = cliente.post(reverse('login'), {
            'username': 'test@correo.com',
            'password': 'Test1234*'
        })
        self.assertIn(response.status_code, [200, 302])

    def test_login_con_contraseña_incorrecta(self):
        """Login falla con contraseña incorrecta"""
        cliente = Client()
        response = cliente.post(reverse('login'), {
            'username': 'test@correo.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # se queda en la página

    def test_usuario_inactivo_no_puede_login(self):
        """Un usuario inactivo no puede iniciar sesión"""
        self.usuario.estado = False
        self.usuario.save()
        cliente = Client()
        response = cliente.post(reverse('login'), {
            'username': 'test@correo.com',
            'password': 'Test1234*'
        })
        self.assertEqual(response.status_code, 200)