from django.contrib import admin

from reservas.models import Reserva, Agenda

# Register your models here.

admin.site.register(Reserva)
admin.site.register(Agenda)
