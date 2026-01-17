# Sistema de Colores Mejorado - ENCI Platform

## 🎨 Paleta de Colores Principal

### Colores Base
```css
/* Light Mode */
--bg-primary: #f8fafc (slate-50)
--bg-secondary: #f1f5f9 (slate-100)
--bg-surface: #ffffff (white)
--bg-hover: #e2e8f0 (slate-200)

/* Dark Mode */
--bg-primary: #0a0f1e (muy oscuro, casi negro con tinte azul)
--bg-secondary: #111827 (gray-900)
--bg-surface: #1e293b (slate-800)
--bg-hover: #334155 (slate-700)
```

### Colores de Texto
```css
/* Light Mode */
--text-primary: #0f172a (slate-900) - Alto contraste
--text-secondary: #475569 (slate-600)
--text-tertiary: #64748b (slate-500)
--text-muted: #94a3b8 (slate-400)

/* Dark Mode */
--text-primary: #f8fafc (slate-50) - Alto contraste
--text-secondary: #cbd5e1 (slate-300)
--text-tertiary: #94a3b8 (slate-400)
--text-muted: #64748b (slate-500)
```

### Colores de Acción (Botones, Links)
```css
/* Primary (Blue) */
Light: #3b82f6 (blue-500) hover: #2563eb (blue-600)
Dark: #60a5fa (blue-400) hover: #3b82f6 (blue-500)

/* Success (Green) */
Light: #10b981 (emerald-500) hover: #059669 (emerald-600)
Dark: #34d399 (emerald-400) hover: #10b981 (emerald-500)

/* Warning (Yellow) */
Light: #f59e0b (amber-500) hover: #d97706 (amber-600)
Dark: #fbbf24 (amber-400) hover: #f59e0b (amber-500)

/* Danger (Red) */
Light: #ef4444 (red-500) hover: #dc2626 (red-600)
Dark: #f87171 (red-400) hover: #ef4444 (red-500)

/* Info (Cyan) */
Light: #06b6d4 (cyan-500) hover: #0891b2 (cyan-600)
Dark: #22d3ee (cyan-400) hover: #06b6d4 (cyan-500)
```

### Colores de Tarjetas (Cards)
```css
/* Light Mode */
--card-bg: #ffffff
--card-border: #e2e8f0 (slate-200)
--card-hover: #f8fafc (slate-50)
--card-shadow: rgba(15, 23, 42, 0.1) (slate-900 con 10% opacidad)

/* Dark Mode */
--card-bg: #1e293b (slate-800)
--card-border: #334155 (slate-700)
--card-hover: #2d3748 (slate-700 más claro)
--card-shadow: rgba(0, 0, 0, 0.5)
```

### Bordes
```css
/* Light Mode */
--border-light: #e2e8f0 (slate-200)
--border-medium: #cbd5e1 (slate-300)
--border-strong: #94a3b8 (slate-400)

/* Dark Mode */
--border-light: #334155 (slate-700)
--border-medium: #475569 (slate-600)
--border-strong: #64748b (slate-500)
```

## 🎯 Emojis Estandarizados

### Navegación Principal
- 🏠 Home
- 🏢 Empresas
- 📊 Dashboard
- 📈 Analytics
- 🔮 Predicciones
- 🚨 Anomalías
- 🔍 Búsqueda
- 📚 Libro Diario
- 📖 Libro Mayor
- 🧾 Balance
- 💰 Estados Financieros

### ML/AI
- 🤖 Machine Learning
- 🧠 Inteligencia Artificial
- 📊 Métricas
- 📈 Tendencias
- 🔮 Forecasting
- 🎯 Precisión
- ⚡ Performance
- 🌟 Recomendaciones

### Acciones
- ✅ Guardar/Confirmar
- ❌ Cancelar/Eliminar
- ✏️ Editar
- 👁️ Ver
- 📥 Importar
- 📤 Exportar
- 🔄 Actualizar
- ⚙️ Configuración

### Estados
- ✓ Completado
- ⏳ En Proceso
- ⚠️ Advertencia
- 🚫 Error
- ℹ️ Información
- 🔔 Notificación

## 💡 Principios de Diseño

### Contraste
- Mínimo 4.5:1 para texto normal
- Mínimo 3:1 para texto grande
- Mínimo 3:1 para componentes UI

### Consistencia
- Usar la misma clase de color para el mismo propósito
- Mantener jerarquía visual consistente
- Espaciado uniforme

### Accesibilidad
- Nunca usar solo color para información importante
- Iconos y emojis deben tener texto alternativo
- Estados interactivos claramente visibles

## 🎨 Gradientes

### Light Mode
```css
/* Hero/Header */
from-blue-50 via-indigo-50 to-purple-50

/* Cards Premium */
from-white to-slate-50

/* Botones */
from-blue-500 to-blue-600
from-emerald-500 to-emerald-600
from-amber-500 to-amber-600
```

### Dark Mode
```css
/* Hero/Header */
from-slate-950 via-slate-900 to-slate-950

/* Cards Premium */
from-slate-800 to-slate-900

/* Botones */
from-blue-600 to-blue-700
from-emerald-600 to-emerald-700
from-amber-600 to-amber-700
```

## 🔍 Componentes Específicos

### Navbar
```css
Light: bg-white border-slate-200 shadow-sm
Dark: bg-slate-900 border-slate-800 shadow-2xl
```

### Sidebar
```css
Light: bg-slate-50 border-slate-200
Dark: bg-slate-900 border-slate-800
```

### Cards
```css
Light: bg-white border-slate-200 shadow hover:shadow-md
Dark: bg-slate-800 border-slate-700 shadow-xl hover:shadow-2xl
```

### Inputs
```css
Light: bg-white border-slate-300 text-slate-900 focus:border-blue-500 focus:ring-blue-500
Dark: bg-slate-800 border-slate-600 text-slate-100 focus:border-blue-400 focus:ring-blue-400
```

### Tables
```css
Light:
  - Header: bg-slate-100 text-slate-700
  - Row: bg-white border-slate-200
  - Row hover: bg-slate-50
Dark:
  - Header: bg-slate-800 text-slate-200
  - Row: bg-slate-900 border-slate-700
  - Row hover: bg-slate-800
```

### Badges/Pills
```css
Light:
  - Info: bg-blue-100 text-blue-700
  - Success: bg-emerald-100 text-emerald-700
  - Warning: bg-amber-100 text-amber-700
  - Danger: bg-red-100 text-red-700

Dark:
  - Info: bg-blue-900 text-blue-200
  - Success: bg-emerald-900 text-emerald-200
  - Warning: bg-amber-900 text-amber-200
  - Danger: bg-red-900 text-red-200
```
