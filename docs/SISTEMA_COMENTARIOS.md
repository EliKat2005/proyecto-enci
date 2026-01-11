# Sistema de Comentarios Unificado

## Descripción General

El sistema de comentarios permite a los docentes supervisores proporcionar retroalimentación a los estudiantes en todas las secciones del módulo de contabilidad.

## Características Principales

### 1. **Comentarios Unificados Across Todas las Secciones**

Los estudiantes pueden ver comentarios del docente en:
- ✅ Plan de Cuentas (PL)
- ✅ Libro Diario (DI)
- ✅ Libro Mayor (MA)
- ✅ Balance de Comprobación (BC)
- ✅ Estados Financieros (EF)

### 2. **Componente Reutilizable**

Se creó un componente único `_comments_section.html` que unifica el diseño y funcionalidad:
- **Vista para Estudiantes**: Muestra todos los comentarios con diseño elegante
  - **Visibilidad Condicional**: Solo visible si:
    - La empresa está marcada como "visible para supervisor" (`empresa.visible_to_supervisor = True`)
    - Y ya existen comentarios del docente
- **Vista para Docentes**: Formulario para agregar nuevos comentarios
  - **Visibilidad**: Siempre visible para supervisores si `empresa.visible_to_supervisor = True`
- **Validación**: Requiere mínimo 10 caracteres
- **Feedback Visual**: Usa `customAlert()` para validaciones

### 3. **Notificaciones Automáticas**

Cuando un docente agrega un comentario:
1. Se crea automáticamente una notificación para el estudiante (dueño de la empresa)
2. La notificación incluye:
   - Nombre del docente que comentó
   - Sección específica donde se comentó
   - Botón "Ir al comentario" con enlace directo
3. El enlace incluye un anchor `#comments-section` para scroll automático

### 4. **Diseño Profesional**

#### Estudiantes ven:
- 🎨 Gradiente emerald en el encabezado
- 👤 Avatares circulares con iniciales del docente
- 🏷️ Badge "Docente" en cada comentario
- ⏰ Timestamps relativos (ej: "hace 2 horas")
- 📝 Mensaje cuando no hay comentarios

#### Docentes ven:
- 📝 Formulario limpio para agregar comentarios
- ✅ Validación en tiempo real (mínimo 10 caracteres)
- 🎯 Botón "Publicar Comentario" con animaciones

## Implementación Técnica

### Modelo: `EmpresaComment`

```python
class EmpresaComment(models.Model):
    SECTION_CHOICES = [
        ("PL", "Plan de Cuentas"),
        ("DI", "Libro Diario"),
        ("MA", "Libro Mayor"),
        ("BC", "Balance de Comprobación"),
        ("EF", "Estados Financieros"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="comments")
    section = models.CharField(max_length=2, choices=SECTION_CHOICES)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # Más recientes primero
```

### Vista: `add_comment`

Responsabilidades:
1. Validar que el usuario sea supervisor de la empresa
2. Crear el comentario
3. Crear notificación para el estudiante
4. Redirigir con anchor a la sección de comentarios

```python
section_urls = {
    "PL": reverse("contabilidad:company_plan", args=[empresa.id]) + "#comments-section",
    "DI": reverse("contabilidad:company_diario", args=[empresa.id]) + "#comments-section",
    "MA": reverse("contabilidad:company_mayor", args=[empresa.id]) + "#comments-section",
    "BC": reverse("contabilidad:company_balance_comprobacion", args=[empresa.id]) + "#comments-section",
    "EF": reverse("contabilidad:company_estados_financieros", args=[empresa.id]) + "#comments-section",
}
```

### Contexto de Templates

Todas las vistas pasan estos valores al contexto:
```python
context = {
    "comments": empresa.comments.filter(section="XX").select_related("author").order_by("-created_at"),
    "is_docente": request.user.userprofile.rol == UserProfile.Roles.DOCENTE,
    "is_supervisor": EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists(),
    # ... otros campos
}
```

### Integración en Templates

Cada template incluye el componente al final:
```django
{% include 'contabilidad/_comments_section.html' with section_code='PL' %}
```

## Flujo de Usuario

### Para Estudiantes:

1. **Configurar visibilidad**:
   - El estudiante debe marcar la empresa como "visible para supervisor"
   - Sin esta configuración, la sección de comentarios NO será visible

2. **Recibir notificación**:
   - Aparece badge de notificación en navbar cuando el docente comenta
   - Notificación muestra: "Dr. Juan Pérez ha dejado un comentario en Plan de Cuentas"

3. **Ir al comentario**:
   - Click en botón "Ir al comentario" (emerald verde)
   - Redirección a la página correcta
   - Scroll automático a la sección de comentarios

4. **Ver comentarios**:
   - Lista organizada de más reciente a más antiguo
   - Nombre del docente, timestamp, contenido
   - Solo visible si empresa.visible_to_supervisor Y hay comentarios

### Para Docentes:

1. **Verificar visibilidad**:
   - Solo pueden comentar en empresas marcadas como "visible para supervisor"
   - Si la empresa no es visible, no verán el formulario de comentarios

2. **Navegar a cualquier sección** (Plan, Diario, Mayor, Balance, Estados)

3. **Escribir comentario**:
   - Formulario siempre visible al final de la página (si empresa es visible)
   - Validación: mínimo 10 caracteres
   - Si es muy corto: alerta con `customAlert()`

4. **Publicar**:
   - Click en "Publicar Comentario"
   - Notificación automática enviada al estudiante
   - Redirección de vuelta a la misma sección

## Ventajas del Sistema

✅ **Consistencia**: Mismo diseño en todas las secciones
✅ **Mantenibilidad**: Un solo componente para actualizar
✅ **UX Mejorada**: Navegación directa con anchors
✅ **Feedback Claro**: Notificaciones automáticas
✅ **Validación**: Previene comentarios vacíos o muy cortos
✅ **Escalabilidad**: Fácil agregar nuevas secciones
✅ **Privacidad**: Solo visible si estudiante lo permite
✅ **Condicional**: Aparece solo cuando hay contenido útil
  - `company_balance_comprobacion`: Contexto de comentarios agregado
  - `company_estados_financieros`: Contexto de comentarios agregado

### Templates
- **Nuevo**: `templates/contabilidad/_comments_section.html`
- **Actualizado**:
  - `company_plan.html`
  - `company_diario.html`
  - `company_mayor.html`
  - `company_balance_comprobacion.html`
  - `company_estados_financieros.html`
  - `core/notifications.html`: Etiquetas de sección actualizadas, botón "Ir" mejorado

### Migraciones
- `0020_alter_empresacomment_options_and_more.py`: Nuevo SECTION_CHOICES y ordering

## Testing

Para probar el sistema:

1. **Como docente**:
   ```bash
   # Login como docente supervisor
   # Navegar a cualquier empresa que supervises
   # Ir a cualquier sección (Plan, Diario, Mayor, Balance, Estados)
   # Agregar comentario con al menos 10 caracteres
   # Verificar redirección con scroll a comentarios
   ```

2. **Como estudiante**:
   ```bash
   # Login como estudiante
   # Verificar badge de notificación en navbar
   # Click en notificaciones
   # Click en "Ir al comentario"
   # Verificar que te lleva a la página correcta con scroll
   # Ver comentario en la sección de comentarios
   ```

## Mejoras Futuras (Opcional)

- [ ] Edición de comentarios por el autor
- [ ] Eliminación de comentarios por el autor
- [ ] Respuestas a comentarios (threading)
- [ ] Menciones con @ (ej: @estudiante)
- [ ] Archivos adjuntos en comentarios
- [ ] Rich text editor para comentarios
- [ ] Marcado de comentarios como "resueltos"

## Notas de Desarrollo

- El componente `_comments_section.html` usa TailwindCSS
- Los modals usan el sistema `customAlert()` de `base.html`
- Las notificaciones usan el modelo `Notification` de core
- El anchor `#comments-section` debe coincidir con el ID en el componente
- Los docentes pueden comentar aunque no sean el owner de la empresa
