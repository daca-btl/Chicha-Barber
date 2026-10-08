from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from core.views import inicio, inicio_admin, CustomLoginView
from usuarios import views as views_usuarios

# 🔥 IMPORTANTE para imágenes
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', inicio, name='inicio'),
    path('api/', include('reportes.urls')),

    # --- APPS DEL PROYECTO ---
    path('servicios/', include('servicios.urls')),
    path('reservas/', include('reservas.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('catalogo/', include('catalogo.urls')),
    path('productos/', include('catalogo.urls')),  # Compatibilidad
    path('compras/', include('compra.urls')),
    path('ventas/', include('venta.urls')),
    path('historial/', include('historial.urls')),
    path('configuracion/', include('configuraciones.urls')),
    path('', include('venta.urls')),  # Carrito, pago y checkout directo

    path('panel/', inicio_admin, name='inicio_admin'),

    # --- AUTENTICACIÓN Y PASSWORD RESET ---
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='inicio'), name='logout'),

    # 🔥 VISTA PERSONALIZADA - usa core/utils.py para el correo
    path('recuperar-password/', views_usuarios.recuperar_password_view, name='password_reset'),

    path('recuperar-password/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='registration/recuperar_enviado.html'), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/recuperar_confirmar.html'), name='password_reset_confirm'),
    path('recuperar/completo/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/recuperar_completo.html'), name='password_reset_complete'),
    
    #ia - chat
   path('chat/', include('chat_ia.urls')),

   
   
   
 
    # ... tus otras urls
    
]


# 🔥 ESTO HACE QUE LAS IMÁGENES FUNCIONEN
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)