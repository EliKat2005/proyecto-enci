from django.conf import settings
from django.db import models


# --- Clases de Opciones (ENUMs) ---

class TipoCuenta(models.TextChoices):
    ACTIVO = 'Activo', 'Activo'
    PASIVO = 'Pasivo', 'Pasivo'
    PATRIMONIO = 'Patrimonio', 'Patrimonio'
    INGRESO = 'Ingreso', 'Ingreso'
    COSTO = 'Costo', 'Costo'
    GASTO = 'Gasto', 'Gasto'

class NaturalezaCuenta(models.TextChoices):
    DEUDORA = 'Deudora', 'Deudora'
    ACREEDORA = 'Acreedora', 'Acreedora'

class EstadoAsiento(models.TextChoices):
    BORRADOR = 'Borrador', 'Borrador'
    CONFIRMADO = 'Confirmado', 'Confirmado'


# --- Modelos de Tablas ---

class PlanDeCuentas(models.Model):
    """
    Modelo para el Plan de Cuentas.
    Representa la tabla 'contabilidad_plandecuentas'.
    """
    codigo = models.CharField(unique=True, max_length=50)
    descripcion = models.CharField(max_length=255)
    
    tipo = models.CharField(
        max_length=10, 
        choices=TipoCuenta.choices
    )
    naturaleza = models.CharField(
        max_length=9, 
        choices=NaturalezaCuenta.choices
    )
    
    # inspectdb los vio como Integer, los corregimos a BooleanField
    estado_situacion = models.BooleanField(
        db_comment='True si es cuenta de Balance, False si es de Resultado'
    )
    es_auxiliar = models.BooleanField(
        default=False, 
        db_comment='True si es una cuenta hoja (auxiliar) que puede recibir transacciones'
    )
    
    # Relación recursiva (Padre-Hijo)
    padre = models.ForeignKey(
        'self', 
        on_delete=models.PROTECT, # ON DELETE RESTRICT = models.PROTECT en Django
        blank=True, 
        null=True, 
        db_comment='Clave foránea recursiva para la estructura de árbol'
    )

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_plandecuentas'
        verbose_name = 'Plan de Cuenta'
        verbose_name_plural = 'Planes de Cuentas'

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


class Asiento(models.Model):
    """
    Modelo para la cabecera del Asiento Contable.
    Representa la tabla 'contabilidad_asiento'.
    """
    fecha = models.DateField()
    descripcion_general = models.TextField()
    
    estado = models.CharField(
        max_length=10, 
        choices=EstadoAsiento.choices, 
        default=EstadoAsiento.BORRADOR
    )
    
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT # ON DELETE RESTRICT
    )
    
    # Hacemos que Django maneje las fechas automáticamente
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_asiento'
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'

    def __str__(self):
        return f"Asiento #{self.id} ({self.fecha}) - {self.descripcion_general[:50]}..."


class Transaccion(models.Model):
    """
    Modelo para el detalle (líneas) del Asiento Contable.
    Representa la tabla 'contabilidad_transaccion'.
    """
    asiento = models.ForeignKey(
        Asiento, 
        on_delete=models.CASCADE # ON DELETE CASCADE
    )
    cuenta = models.ForeignKey(
        PlanDeCuentas, 
        on_delete=models.PROTECT # ON DELETE RESTRICT
    )
    
    detalle_linea = models.CharField(max_length=500, blank=True, null=True)
    parcial = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    debe = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)
    haber = models.DecimalField(max_digits=19, decimal_places=2, default=0.00)

    class Meta:
        managed = False # Django no gestionará esta tabla
        db_table = 'contabilidad_transaccion'
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'

    def __str__(self):
        return f"Línea de Asiento #{self.asiento.id}: {self.cuenta.codigo} | D:{self.debe} H:{self.haber}"