#!/usr/bin/env python
"""
Script para asignar automáticamente los padres de las cuentas basándose en su código.
Por ejemplo: 3.1 debe tener como padre a 3, y 3.1.1 debe tener como padre a 3.1
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contabilidad.models import EmpresaPlanCuenta

def asignar_padres_automaticamente(empresa_id=1):
    """Asigna automáticamente los padres de las cuentas basándose en su código."""
    
    # Obtener todas las cuentas de la empresa ordenadas por código
    cuentas = EmpresaPlanCuenta.objects.filter(empresa_id=empresa_id).order_by('codigo')
    
    # PASO 1: Identificar qué cuentas deberían ser NO auxiliares (tienen subcuentas potenciales)
    codigos_con_hijas = set()
    for cuenta in cuentas:
        partes = cuenta.codigo.split('.')
        if len(partes) > 1:
            # El código del padre es todo menos la última parte
            codigo_padre = '.'.join(partes[:-1])
            codigos_con_hijas.add(codigo_padre)
    
    print("PASO 1: Corrigiendo cuentas que deberían ser NO auxiliares...")
    corregidas = 0
    for cuenta in cuentas:
        if cuenta.codigo in codigos_con_hijas and cuenta.es_auxiliar:
            cuenta.es_auxiliar = False
            # Guardar sin validaciones para evitar problemas circulares
            EmpresaPlanCuenta.objects.filter(pk=cuenta.pk).update(es_auxiliar=False)
            corregidas += 1
            print(f"  ✓ {cuenta.codigo} - {cuenta.descripcion} → Marcada como NO auxiliar (tiene subcuentas)")
    
    print(f"\nCuentas corregidas: {corregidas}\n")
    
    # PASO 2: Asignar padres
    print("PASO 2: Asignando padres automáticamente...")
    actualizadas = 0
    errores = 0
    
    for cuenta in cuentas:
        # Si la cuenta ya tiene padre, no hacer nada
        if cuenta.padre:
            continue
        
        # Obtener el código del padre esperado
        partes = cuenta.codigo.split('.')
        
        # Si solo tiene una parte (ej: "1", "2", "3"), no tiene padre
        if len(partes) == 1:
            print(f"✓ {cuenta.codigo} - {cuenta.descripcion} (sin padre, es raíz)")
            continue
        
        # El código del padre es todo menos la última parte
        codigo_padre = '.'.join(partes[:-1])
        
        # Buscar el padre
        try:
            padre = EmpresaPlanCuenta.objects.get(empresa_id=empresa_id, codigo=codigo_padre)
            # Actualizar directamente sin validaciones
            EmpresaPlanCuenta.objects.filter(pk=cuenta.pk).update(padre_id=padre.pk)
            actualizadas += 1
            print(f"✓ {cuenta.codigo} - {cuenta.descripcion} → Padre: {padre.codigo} - {padre.descripcion}")
        except EmpresaPlanCuenta.DoesNotExist:
            errores += 1
            print(f"✗ {cuenta.codigo} - {cuenta.descripcion} → Padre esperado '{codigo_padre}' NO EXISTE")
    
    print(f"\n{'='*60}")
    print(f"Cuentas con padres asignados: {actualizadas}")
    print(f"Errores: {errores}")
    print(f"{'='*60}")

if __name__ == '__main__':
    asignar_padres_automaticamente()
