"""Formularios para el sistema de Kardex (inventarios)."""

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    EmpresaPlanCuenta,
    EmpresaTercero,
    ProductoInventario,
    TipoMovimientoKardex,
)


class ProductoInventarioForm(forms.ModelForm):
    """Formulario para crear/editar productos de inventario."""

    class Meta:
        model = ProductoInventario
        fields = [
            "sku",
            "nombre",
            "descripcion",
            "categoria",
            "unidad_medida",
            "metodo_valoracion",
            "cuenta_inventario",
            "cuenta_costo_venta",
            "stock_minimo",
            "stock_maximo",
            "activo",
        ]
        widgets = {
            "sku": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "PROD-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "Laptop Dell XPS 15",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "rows": 3,
                    "placeholder": "Descripción detallada del producto (opcional)",
                }
            ),
            "categoria": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "Electrónica, Oficina, etc.",
                }
            ),
            "unidad_medida": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "unidad, caja, kg, etc.",
                }
            ),
            "metodo_valoracion": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                }
            ),
            "cuenta_inventario": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                }
            ),
            "cuenta_costo_venta": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
                }
            ),
            "stock_minimo": forms.NumberInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "10",
                    "step": "0.001",
                }
            ),
            "stock_maximo": forms.NumberInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                    "placeholder": "100",
                    "step": "0.001",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "w-5 h-5 text-purple-600 border-gray-300 dark:border-gray-600 rounded focus:ring-purple-500"
                }
            ),
        }
        labels = {
            "sku": "Código SKU",
            "nombre": "Nombre del Producto",
            "descripcion": "Descripción",
            "categoria": "Categoría",
            "unidad_medida": "Unidad de Medida",
            "metodo_valoracion": "Método de Valoración",
            "cuenta_inventario": "Cuenta Contable - Inventario",
            "cuenta_costo_venta": "Cuenta Contable - Costo de Venta",
            "stock_minimo": "Stock Mínimo",
            "stock_maximo": "Stock Máximo",
            "activo": "Producto Activo",
        }
        help_texts = {
            "sku": "Código único del producto (ej: LAPTOP-001)",
            "metodo_valoracion": "PROMEDIO: costo promedio ponderado (recomendado)",
            "cuenta_inventario": "Cuenta donde se registra el valor del inventario (Activo)",
            "cuenta_costo_venta": "Cuenta donde se registra el costo al vender (Gasto)",
            "stock_minimo": "Alerta si el stock cae por debajo de este valor",
            "stock_maximo": "Stock máximo recomendado",
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa

        # Filtrar cuentas por empresa
        if empresa:
            self.fields["cuenta_inventario"].queryset = EmpresaPlanCuenta.objects.filter(
                empresa=empresa
            ).order_by("codigo")
            self.fields["cuenta_costo_venta"].queryset = EmpresaPlanCuenta.objects.filter(
                empresa=empresa
            ).order_by("codigo")

        # Campo empresa oculto
        if empresa and not self.instance.pk:
            self.instance.empresa = empresa

    def clean_sku(self):
        """Validar que el SKU sea único para la empresa."""
        sku = self.cleaned_data["sku"].strip().upper()

        # Verificar unicidad en la empresa
        queryset = ProductoInventario.objects.filter(empresa=self.empresa, sku=sku)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError(f"Ya existe un producto con el SKU '{sku}' en esta empresa.")

        return sku

    def clean(self):
        """Validaciones adicionales."""
        cleaned_data = super().clean()
        stock_minimo = cleaned_data.get("stock_minimo")
        stock_maximo = cleaned_data.get("stock_maximo")

        if stock_minimo and stock_maximo:
            if stock_minimo > stock_maximo:
                raise ValidationError(
                    {"stock_minimo": "El stock mínimo no puede ser mayor que el máximo."}
                )

        return cleaned_data


class MovimientoKardexForm(forms.Form):
    """Formulario para registrar movimientos de inventario (Entrada/Salida).

    Este formulario NO usa ModelForm porque los movimientos se crean
    a través de KardexService, que calcula automáticamente los saldos.
    """

    tipo_movimiento = forms.ChoiceField(
        label="Tipo de Movimiento",
        choices=TipoMovimientoKardex.choices,
        widget=forms.RadioSelect(
            attrs={
                "class": "text-purple-600 border-gray-300 dark:border-gray-600 focus:ring-purple-500"
            }
        ),
    )

    fecha = forms.DateField(
        label="Fecha del Movimiento",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
            }
        ),
        help_text="Fecha en la que ocurrió la entrada o salida",
    )

    cantidad = forms.DecimalField(
        label="Cantidad",
        max_digits=15,
        decimal_places=3,
        min_value=0.001,
        widget=forms.NumberInput(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                "placeholder": "10.000",
                "step": "0.001",
            }
        ),
        help_text="Cantidad de unidades a registrar",
    )

    costo_unitario = forms.DecimalField(
        label="Costo Unitario",
        max_digits=15,
        decimal_places=6,
        min_value=0,
        required=False,  # Solo requerido para entradas
        widget=forms.NumberInput(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                "placeholder": "1500.000000",
                "step": "0.000001",
            }
        ),
        help_text="Costo unitario (requerido solo para ENTRADAS)",
    )

    documento_referencia = forms.CharField(
        label="Documento de Referencia",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                "placeholder": "FAC-12345, OC-6789, etc.",
            }
        ),
        help_text="Número de factura, orden de compra, etc.",
    )

    tercero = forms.ModelChoiceField(
        label="Tercero (Proveedor/Cliente)",
        queryset=EmpresaTercero.objects.none(),
        required=False,
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100"
            }
        ),
        help_text="Proveedor (para entradas) o Cliente (para salidas)",
    )

    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-gray-100",
                "rows": 3,
                "placeholder": "Notas adicionales sobre el movimiento (opcional)",
            }
        ),
    )

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto

        # Filtrar terceros por empresa del producto
        if producto:
            self.fields["tercero"].queryset = EmpresaTercero.objects.filter(
                empresa=producto.empresa
            ).order_by("nombre")

    def clean(self):
        """Validaciones adicionales."""
        cleaned_data = super().clean()
        tipo_movimiento = cleaned_data.get("tipo_movimiento")
        costo_unitario = cleaned_data.get("costo_unitario")
        cantidad = cleaned_data.get("cantidad")

        # Para ENTRADAS, el costo unitario es obligatorio
        if tipo_movimiento in [
            TipoMovimientoKardex.ENTRADA,
            TipoMovimientoKardex.DEVOLUCION_VENTA,
            TipoMovimientoKardex.AJUSTE_ENTRADA,
        ]:
            if not costo_unitario or costo_unitario <= 0:
                raise ValidationError(
                    {
                        "costo_unitario": "El costo unitario es obligatorio para entradas y debe ser mayor a 0."
                    }
                )

        # Para SALIDAS, validar que haya stock suficiente
        if tipo_movimiento in [
            TipoMovimientoKardex.SALIDA,
            TipoMovimientoKardex.DEVOLUCION_COMPRA,
            TipoMovimientoKardex.AJUSTE_SALIDA,
        ]:
            if self.producto and cantidad:
                stock_actual = self.producto.stock_actual
                if cantidad > stock_actual:
                    raise ValidationError(
                        {
                            "cantidad": f"Stock insuficiente. Disponible: {stock_actual} {self.producto.unidad_medida}"
                        }
                    )

        return cleaned_data
