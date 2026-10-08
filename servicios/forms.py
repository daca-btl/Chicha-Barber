import re

from django import forms
from django.forms import ModelForm
from .models import Servicios, Calificacion


class ValidacionServicioMixin:
    nombre_pattern = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s]+$'

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not re.fullmatch(self.nombre_pattern, nombre):
            raise forms.ValidationError(
                'El nombre solo puede contener letras, números y espacios.'
            )
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio < 0:
            raise forms.ValidationError('El precio no puede ser negativo.')
        return precio

    def clean_duracion(self):
        duracion = self.cleaned_data.get('duracion')
        if duracion is not None and duracion < 1:
            raise forms.ValidationError(
                'La duración debe ser de al menos un minuto.'
            )
        return duracion


class ServiciosForm(ValidacionServicioMixin, ModelForm):
    class Meta:
        model = Servicios
        fields = ['nombre', 'precio', 'duracion', 'descripcion', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Corte de cabello',
                'pattern': ValidacionServicioMixin.nombre_pattern,
                'title': 'El nombre solo puede contener letras, números y espacios.',
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'title': 'El precio no puede ser negativo.',
            }),
            'duracion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'title': 'La duración debe ser de al menos un minuto.',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }


class ServiciosEditarForm(ValidacionServicioMixin, ModelForm):
    class Meta:
        model = Servicios
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': ValidacionServicioMixin.nombre_pattern,
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
            }),
            'duracion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'estado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class CalificacionForm(ModelForm):
    class Meta:
        model = Calificacion
        # Se quita 'cliente' — ahora se asigna automáticamente
        # en la vista con request.user, no lo llena el usuario a mano.
        fields = ['servicio', 'puntuacion', 'comentario']
        widgets = {
            'servicio': forms.Select(attrs={'class': 'form-control'}),
            'puntuacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
           
        }

        
        

class ResponderCalificacionForm(forms.Form):
    respuesta = forms.CharField(
        label='Escribe tu respuesta',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Escribe aquí tu respuesta al cliente...'}),
        required=True
        
    )
    
    

