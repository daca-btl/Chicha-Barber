import re

from django import forms

from .models import (
    Producto,
    Categoria,
    Proveedor,
    Marca,
    DetalleProducto,
    Promocion,
)


# ==========================================================
# VALIDACIONES GENERALES
# ==========================================================

def validar_texto(valor, campo):
    """
    Valida campos que pueden contener:
    letras, números, espacios y caracteres propios
    de letras en español.
    """

    if not valor:
        raise forms.ValidationError(
            f'El campo {campo} es obligatorio.'
        )

    valor = valor.strip()

    if not re.fullmatch(
        r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+',
        valor
    ):
        raise forms.ValidationError(
            f'El campo {campo} solo puede contener '
            'letras, números y espacios.'
        )

    return valor


def validar_descripcion(valor, campo):
    """
    Valida descripciones permitiendo algunos caracteres
    útiles como punto, coma, dos puntos, #, *, /, (), guion y guion bajo.
    """

    if not valor:
        return valor

    valor = valor.strip()

    if not re.fullmatch(
        r'[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s.,:#*/()_-]+',
        valor
    ):
        raise forms.ValidationError(
            f'El campo {campo} contiene caracteres no permitidos.'
        )

    return valor


# ==========================================================
# FORMULARIO PRODUCTO
# ==========================================================

class ProductoForm(forms.ModelForm):

    class Meta:
        model = Producto

        fields = [
            'nombre',
            'descripcion',
            'codigo_categoria',
            'codigo_marca',
            'precio',
            'imagen',
            'estado',
        ]

        widgets = {

            # ==================================================
            # NOMBRE DEL PRODUCTO
            # Letras, números, tildes, ñ y espacios
            # ==================================================

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre del producto',

                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s]+$'
                    ),

                    'title': (
                        'El nombre del producto solo puede '
                        'contener letras y espacios. '
                        'No se permiten números ni caracteres especiales.'
                    ),
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Descripción del producto',
                }
            ),

            'codigo_categoria': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'codigo_marca': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'precio': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'step': '0.01',
                    'placeholder': 'Precio',
                }
            ),

            'imagen': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                }
            ),

            'estado': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

        labels = {
            'nombre': 'Nombre del Producto',
            'descripcion': 'Descripción',
            'codigo_categoria': 'Categoría',
            'codigo_marca': 'Marca',
            'precio': 'Precio',
            'imagen': 'Imagen',
            'estado': 'Activo',
        }

    # ======================================================
    # FILTRAR MARCAS ACTIVAS
    # ======================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo mostrar marcas activas
        if 'codigo_marca' in self.fields:

            self.fields['codigo_marca'].queryset = (
                Marca.objects
                .filter(estado=True)
                .order_by('nombre')
            )

            self.fields['codigo_marca'].empty_label = (
                'Seleccione una marca (opcional)'
            )

    # ======================================================
    # VALIDAR MARCA
    # ======================================================

    def clean_codigo_marca(self):

        marca = self.cleaned_data.get('codigo_marca')

        if marca is not None and not marca.estado:

            raise forms.ValidationError(
                'No se puede asignar una marca inactiva '
                'a un producto.'
            )

        return marca

    # ======================================================
    # VALIDAR NOMBRE DEL PRODUCTO
    # Letras, números y espacios
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        if not nombre:

            raise forms.ValidationError(
                'El nombre del producto es obligatorio.'
            )

        nombre = nombre.strip()

        if len(nombre) < 2:

            raise forms.ValidationError(
                'El nombre del producto debe tener '
                'al menos 2 caracteres.'
            )

        # Letras, números, tildes, ñ y espacios
        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\s]+',
            nombre
        ):

            raise forms.ValidationError(
                'El nombre del producto solo puede contener '
                'letras, números y espacios.'
            )

        return nombre

    # ======================================================
    # VALIDAR DESCRIPCIÓN
    # ======================================================

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get('descripcion')

        return validar_descripcion(
            descripcion,
            'descripción'
        )

    # ======================================================
    # VALIDAR PRECIO
    # ======================================================

    def clean_precio(self):

        precio = self.cleaned_data.get('precio')

        if precio is not None and precio < 0:

            raise forms.ValidationError(
                'El precio no puede ser negativo.'
            )

        return precio


# ==========================================================
# FORMULARIO DETALLE PRODUCTO
# STOCK / EXISTENCIAS
# ==========================================================

class DetalleProductoForm(forms.ModelForm):

    class Meta:
        model = DetalleProducto

        fields = [
            'cantidad_actual',
            'stock_min',
            'stock_max',
            'observaciones',
        ]

        widgets = {

            'cantidad_actual': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'step': '1',
                }
            ),

            'stock_min': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'step': '1',
                }
            ),

            'stock_max': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'step': '1',
                }
            ),

            'observaciones': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Observaciones',
                }
            ),
        }

        labels = {
            'cantidad_actual': 'Cantidad Actual',
            'stock_min': 'Stock Mínimo',
            'stock_max': 'Stock Máximo',
            'observaciones': 'Observaciones',
        }

    # ======================================================
    # VALIDAR CANTIDAD
    # ======================================================

    def clean_cantidad_actual(self):

        cantidad = self.cleaned_data.get(
            'cantidad_actual'
        )

        if cantidad is not None and cantidad < 0:

            raise forms.ValidationError(
                'La cantidad actual no puede ser negativa.'
            )

        return cantidad

    # ======================================================
    # VALIDAR STOCK MÍNIMO
    # ======================================================

    def clean_stock_min(self):

        stock_min = self.cleaned_data.get(
            'stock_min'
        )

        if stock_min is not None and stock_min < 0:

            raise forms.ValidationError(
                'El stock mínimo no puede ser negativo.'
            )

        return stock_min

    # ======================================================
    # VALIDAR STOCK MÁXIMO
    # ======================================================

    def clean_stock_max(self):

        stock_max = self.cleaned_data.get(
            'stock_max'
        )

        if stock_max is not None and stock_max < 0:

            raise forms.ValidationError(
                'El stock máximo no puede ser negativo.'
            )

        return stock_max

    # ======================================================
    # VALIDAR RELACIÓN STOCK MÍNIMO / MÁXIMO
    # ======================================================

    def clean(self):

        cleaned_data = super().clean()

        stock_min = cleaned_data.get('stock_min')
        stock_max = cleaned_data.get('stock_max')

        if (
            stock_min is not None
            and stock_max is not None
            and stock_max < stock_min
        ):

            raise forms.ValidationError(
                'El stock máximo no puede ser menor '
                'que el stock mínimo.'
            )

        return cleaned_data


# ==========================================================
# FORMULARIO CATEGORÍA
# ==========================================================

class CategoriaForm(forms.ModelForm):

    class Meta:
        model = Categoria

        fields = [
            'nombre',
            'descripcion',
        ]

        widgets = {

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control border-secondary',
                    'placeholder': (
                        'Ingrese el nombre de la categoría'
                    ),
                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
                    ),
                    'title': (
                        'Solo se permiten letras, números '
                        'y espacios.'
                    ),
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control border-secondary',
                    'placeholder': (
                        'Descripción de la categoría'
                    ),
                    'rows': 4,
                }
            ),
        }

        labels = {
            'nombre': 'Nombre de Categoría',
            'descripcion': 'Descripción',
        }

    # ======================================================
    # VALIDAR NOMBRE
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        return validar_texto(
            nombre,
            'nombre de la categoría'
        )

    # ======================================================
    # VALIDAR DESCRIPCIÓN
    # ======================================================

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get('descripcion')

        return validar_descripcion(
            descripcion,
            'descripción'
        )


# ==========================================================
# FORMULARIO PROVEEDOR
# ==========================================================

class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor

        fields = [
            'nombre',
            'telefono',
            'correo',
            'direccion',
        ]

        widgets = {

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre del proveedor',
                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
                    ),
                    'title': (
                        'Solo se permiten letras, números '
                        'y espacios.'
                    ),
                }
            ),

            'telefono': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '3001234567',
                    'pattern': r'^[0-9]+$',
                    'inputmode': 'numeric',
                    'title': (
                        'El teléfono solo puede contener números.'
                    ),
                }
            ),

            'correo': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'correo@ejemplo.com',
                }
            ),

            'direccion': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Calle 10 # 20-30',
                }
            ),
        }

        labels = {
            'nombre': 'Nombre del Proveedor',
            'telefono': 'Teléfono',
            'correo': 'Correo Electrónico',
            'direccion': 'Dirección',
        }

    # ======================================================
    # VALIDAR NOMBRE
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        return validar_texto(
            nombre,
            'nombre del proveedor'
        )

    # ======================================================
    # VALIDAR TELÉFONO
    # ======================================================

    def clean_telefono(self):

        telefono = self.cleaned_data.get('telefono')

        if not telefono:
            return telefono

        telefono = telefono.strip()

        if not telefono.isdigit():

            raise forms.ValidationError(
                'El teléfono solo puede contener números.'
            )

        if len(telefono) < 7 or len(telefono) > 15:

            raise forms.ValidationError(
                'El teléfono debe tener entre 7 y 15 números.'
            )

        return telefono

    # ======================================================
    # VALIDAR DIRECCIÓN
    # ======================================================

    def clean_direccion(self):

        direccion = self.cleaned_data.get('direccion')

        if not direccion:
            return direccion

        direccion = direccion.strip()

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,#*/()_-]+',
            direccion
        ):

            raise forms.ValidationError(
                'La dirección contiene caracteres no permitidos.'
            )

        return direccion


# ==========================================================
# FORMULARIO MARCA
# ==========================================================

class MarcaForm(forms.ModelForm):

    class Meta:
        model = Marca

        fields = [
            'nombre',
            'descripcion',
            'estado',
        ]

        widgets = {

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre de la marca',
                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
                    ),
                    'title': (
                        'El nombre solo puede contener '
                        'letras, números y espacios.'
                    ),
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Descripción de la marca',
                    'rows': 3,
                }
            ),

            'estado': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

        labels = {
            'nombre': 'Nombre de la Marca',
            'descripcion': 'Descripción',
            'estado': 'Activo',
        }

    # ======================================================
    # VALIDAR NOMBRE
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        if not nombre:

            raise forms.ValidationError(
                'El nombre de la marca es obligatorio.'
            )

        nombre = nombre.strip()

        if len(nombre) < 2:

            raise forms.ValidationError(
                'El nombre debe tener al menos 2 caracteres.'
            )

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+',
            nombre
        ):

            raise forms.ValidationError(
                'El nombre solo puede contener letras, '
                'números y espacios.'
            )

        return nombre

    # ======================================================
    # VALIDAR DESCRIPCIÓN
    # ======================================================

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get(
            'descripcion'
        )

        return validar_descripcion(
            descripcion,
            'descripción'
        )


# ==========================================================
# FORMULARIO PROMOCIÓN
# ==========================================================

class PromocionForm(forms.ModelForm):

    class Meta:
        model = Promocion

        fields = [
            'codigo_servicio',
            'codigo_producto',
            'nombre',
            'porcentaje_descuento',
            'fecha_inicio',
            'fecha_fin',
            'descripcion',
            'imagen',
            'estado',
        ]

        widgets = {

            'codigo_servicio': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'codigo_producto': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': (
                        'Ej. Promoción de Verano'
                    ),
                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
                    ),
                    'title': (
                        'El nombre solo puede contener '
                        'letras, números y espacios.'
                    ),
                }
            ),

            'porcentaje_descuento': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': '50',
                    'step': '0.01',
                    'placeholder': 'Ej. 20',
                    'title': (
                        'El descuento debe estar '
                        'entre 0 y 50.'
                    ),
                }
            ),

            'fecha_inicio': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),

            'fecha_fin': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': (
                        'Descripción de la promoción'
                    ),
                    'rows': 3,
                }
            ),

            'imagen': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                }
            ),

            'estado': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

        labels = {
            'codigo_servicio': 'Servicio Asociado',
            'codigo_producto': 'Producto Asociado',
            'nombre': 'Nombre de la Promoción',
            'porcentaje_descuento': (
                'Porcentaje de Descuento'
            ),
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Fin',
            'descripcion': 'Descripción',
            'imagen': 'Imagen',
            'estado': 'Activo',
        }

    # ======================================================
    # VALIDAR NOMBRE
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        if not nombre:

            raise forms.ValidationError(
                'El nombre de la promoción es obligatorio.'
            )

        nombre = nombre.strip()

        if len(nombre) < 2:

            raise forms.ValidationError(
                'El nombre debe tener al menos 2 caracteres.'
            )

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+',
            nombre
        ):

            raise forms.ValidationError(
                'El nombre solo puede contener '
                'letras, números y espacios.'
            )

        return nombre

    # ======================================================
    # VALIDAR PORCENTAJE
    # ======================================================

    def clean_porcentaje_descuento(self):

        porcentaje = self.cleaned_data.get(
            'porcentaje_descuento'
        )

        if porcentaje is None:

            raise forms.ValidationError(
                'El porcentaje de descuento es obligatorio.'
            )

        if porcentaje < 0 or porcentaje > 50:

            raise forms.ValidationError(
                'El porcentaje de descuento debe estar '
                'entre 0 y 50.'
            )

        return porcentaje

    # ======================================================
    # VALIDAR DESCRIPCIÓN
    # ======================================================

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get(
            'descripcion'
        )

        if not descripcion:
            return descripcion

        descripcion = descripcion.strip()

        if len(descripcion) < 10:

            raise forms.ValidationError(
                'La descripción debe tener al menos '
                '10 caracteres.'
            )

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,#*/()_-]+',
            descripcion
        ):

            raise forms.ValidationError(
                'La descripción contiene caracteres '
                'no permitidos.'
            )

        return descripcion

    # ======================================================
    # VALIDAR FECHAS Y ASOCIACIÓN
    # ======================================================

    def clean(self):

        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get(
            'fecha_inicio'
        )

        fecha_fin = cleaned_data.get(
            'fecha_fin'
        )

        if fecha_inicio and fecha_fin:

            if fecha_fin < fecha_inicio:

                raise forms.ValidationError(
                    'La fecha de finalización no puede '
                    'ser anterior a la fecha de inicio.'
                )

        codigo_producto = cleaned_data.get(
            'codigo_producto'
        )

        codigo_servicio = cleaned_data.get(
            'codigo_servicio'
        )

        if not codigo_producto and not codigo_servicio:

            raise forms.ValidationError(
                'La promoción debe estar asociada '
                'a un producto o a un servicio.'
            )

        return cleaned_data


# ==========================================================
# FORMULARIO EDITAR PROMOCIÓN
# ==========================================================

class PromocionEditarForm(forms.ModelForm):

    class Meta:
        model = Promocion

        fields = [
            'codigo_servicio',
            'codigo_producto',
            'nombre',
            'porcentaje_descuento',
            'fecha_inicio',
            'fecha_fin',
            'descripcion',
            'imagen',
            'estado',
        ]

        widgets = {

            'codigo_servicio': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'codigo_producto': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),

            'nombre': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre de la promoción',
                    'pattern': (
                        r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
                    ),
                }
            ),

            'porcentaje_descuento': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': '50',
                    'step': '0.01',
                }
            ),

            'fecha_inicio': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),

            'fecha_fin': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': (
                        'Descripción de la promoción'
                    ),
                }
            ),

            'imagen': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                }
            ),

            'estado': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

        labels = {
            'codigo_servicio': 'Servicio Asociado',
            'codigo_producto': 'Producto Asociado',
            'nombre': 'Nombre de la Promoción',
            'porcentaje_descuento': (
                'Porcentaje de Descuento'
            ),
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Fin',
            'descripcion': 'Descripción',
            'imagen': 'Imagen',
            'estado': 'Activo',
        }

    # ======================================================
    # VALIDAR NOMBRE
    # ======================================================

    def clean_nombre(self):

        nombre = self.cleaned_data.get('nombre')

        if not nombre:

            raise forms.ValidationError(
                'El nombre de la promoción es obligatorio.'
            )

        nombre = nombre.strip()

        if len(nombre) < 2:

            raise forms.ValidationError(
                'El nombre debe tener al menos 2 caracteres.'
            )

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+',
            nombre
        ):

            raise forms.ValidationError(
                'El nombre solo puede contener '
                'letras, números y espacios.'
            )

        return nombre

    # ======================================================
    # VALIDAR PORCENTAJE
    # ======================================================

    def clean_porcentaje_descuento(self):

        porcentaje = self.cleaned_data.get(
            'porcentaje_descuento'
        )

        if porcentaje is None:

            raise forms.ValidationError(
                'El porcentaje de descuento es obligatorio.'
            )

        if porcentaje < 0 or porcentaje > 50:

            raise forms.ValidationError(
                'El porcentaje de descuento debe estar '
                'entre 0 y 50.'
            )

        return porcentaje

    # ======================================================
    # VALIDAR DESCRIPCIÓN
    # ======================================================

    def clean_descripcion(self):

        descripcion = self.cleaned_data.get(
            'descripcion'
        )

        if not descripcion:
            return descripcion

        descripcion = descripcion.strip()

        if len(descripcion) < 10:

            raise forms.ValidationError(
                'La descripción debe tener al menos '
                '10 caracteres.'
            )

        if not re.fullmatch(
            r'[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,#*/()_-]+',
            descripcion
        ):

            raise forms.ValidationError(
                'La descripción contiene caracteres '
                'no permitidos.'
            )

        return descripcion

    # ======================================================
    # VALIDAR FECHAS Y ASOCIACIÓN
    # ======================================================

    def clean(self):

        cleaned_data = super().clean()

        fecha_inicio = cleaned_data.get(
            'fecha_inicio'
        )

        fecha_fin = cleaned_data.get(
            'fecha_fin'
        )

        if fecha_inicio and fecha_fin:

            if fecha_fin < fecha_inicio:

                raise forms.ValidationError(
                    'La fecha de finalización no puede '
                    'ser anterior a la fecha de inicio.'
                )

        codigo_producto = cleaned_data.get(
            'codigo_producto'
        )

        codigo_servicio = cleaned_data.get(
            'codigo_servicio'
        )

        if not codigo_producto and not codigo_servicio:

            raise forms.ValidationError(
                'La promoción debe estar asociada '
                'a un producto o a un servicio.'
            )

        return cleaned_data
