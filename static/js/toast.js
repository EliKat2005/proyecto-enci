/**
 * 🎉 TOAST NOTIFICATION SYSTEM
 * Sistema de notificaciones toast elegante y moderno
 * Uso:
 *   Toast.success('Guardado exitosamente');
 *   Toast.error('Error al guardar');
 *   Toast.info('Información importante');
 *   Toast.warning('Advertencia');
 */

class Toast {
  static container = null;
  static toastCount = 0;

  /**
   * Inicializa el contenedor de toasts
   */
  static init() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none';
      this.container.style.maxWidth = '400px';
      document.body.appendChild(this.container);
    }
  }

  /**
   * Muestra un toast de éxito
   */
  static success(message, duration = 4000) {
    this.show({
      message,
      type: 'success',
      icon: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>`,
      duration
    });
  }

  /**
   * Muestra un toast de error
   */
  static error(message, duration = 5000) {
    this.show({
      message,
      type: 'error',
      icon: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>`,
      duration
    });
  }

  /**
   * Muestra un toast de información
   */
  static info(message, duration = 4000) {
    this.show({
      message,
      type: 'info',
      icon: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>`,
      duration
    });
  }

  /**
   * Muestra un toast de advertencia
   */
  static warning(message, duration = 4500) {
    this.show({
      message,
      type: 'warning',
      icon: `<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>`,
      duration
    });
  }

  /**
   * Muestra un toast con loading/spinner
   */
  static loading(message) {
    const toastId = this.show({
      message,
      type: 'loading',
      icon: `<svg class="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>`,
      duration: 0, // No se cierra automáticamente
      closeable: false
    });
    return toastId; // Retorna el ID para poder cerrarlo después
  }

  /**
   * Cierra un toast específico por ID
   */
  static close(toastId) {
    const toastElement = document.getElementById(`toast-${toastId}`);
    if (toastElement) {
      this.remove(toastElement);
    }
  }

  /**
   * Muestra un toast genérico
   */
  static show({ message, type, icon, duration, closeable = true }) {
    this.init();

    const toastId = ++this.toastCount;
    const toast = document.createElement('div');
    toast.id = `toast-${toastId}`;
    toast.className = 'pointer-events-auto transform transition-all duration-300 ease-out';

    // Estilos según el tipo
    const styles = {
      success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-700 text-green-800 dark:text-green-200',
      error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-700 text-red-800 dark:text-red-200',
      info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-800 dark:text-blue-200',
      warning: 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-700 text-amber-800 dark:text-amber-200',
      loading: 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200'
    };

    const iconColors = {
      success: 'text-green-600 dark:text-green-400',
      error: 'text-red-600 dark:text-red-400',
      info: 'text-blue-600 dark:text-blue-400',
      warning: 'text-amber-600 dark:text-amber-400',
      loading: 'text-slate-600 dark:text-slate-400'
    };

    toast.innerHTML = `
      <div class="flex items-start gap-3 p-4 rounded-lg border ${styles[type]} shadow-lg backdrop-blur-sm">
        <div class="${iconColors[type]} flex-shrink-0">
          ${icon}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium leading-snug">${message}</p>
        </div>
        ${closeable ? `
          <button
            onclick="Toast.close(${toastId})"
            class="flex-shrink-0 ml-2 hover:opacity-70 transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2 rounded"
            aria-label="Cerrar notificación"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        ` : ''}
      </div>
    `;

    // Animación de entrada
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    this.container.appendChild(toast);

    // Trigger reflow
    toast.offsetHeight;

    // Animar entrada
    requestAnimationFrame(() => {
      toast.style.opacity = '1';
      toast.style.transform = 'translateX(0)';
    });

    // Auto-cerrar si se especifica duración
    if (duration > 0) {
      setTimeout(() => {
        this.remove(toast);
      }, duration);
    }

    return toastId;
  }

  /**
   * Remueve un toast con animación
   */
  static remove(toast) {
    if (!toast) return;

    // Animación de salida
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';

    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  /**
   * Convierte mensajes de Django en toasts
   */
  static showDjangoMessages() {
    const messagesDiv = document.querySelector('.django-messages');
    if (!messagesDiv) return;

    const messages = messagesDiv.querySelectorAll('.message');
    messages.forEach(msg => {
      const level = msg.dataset.level || 'info';
      const text = msg.textContent.trim();

      // Mapear niveles de Django a métodos de toast
      const levelMap = {
        'debug': 'info',
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'error': 'error'
      };

      const toastMethod = levelMap[level] || 'info';
      this[toastMethod](text);
    });

    // Ocultar el contenedor de mensajes de Django
    messagesDiv.style.display = 'none';
  }
}

// Auto-inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    Toast.showDjangoMessages();
  });
} else {
  Toast.showDjangoMessages();
}

// Exponer Toast globalmente
window.Toast = Toast;

// ===== EJEMPLOS DE USO =====
/*
// Éxito
Toast.success('¡Empresa creada exitosamente!');

// Error
Toast.error('No se pudo guardar. Verifica los datos.');

// Info
Toast.info('Recuerda que tienes 3 empresas activas.');

// Warning
Toast.warning('Esta acción no se puede deshacer.');

// Loading (retorna ID para cerrarlo después)
const loadingId = Toast.loading('Guardando datos...');
// ... hacer operación async ...
Toast.close(loadingId);
Toast.success('¡Guardado!');

// Múltiples toasts (se apilan automáticamente)
Toast.success('Primer mensaje');
Toast.info('Segundo mensaje');
Toast.warning('Tercer mensaje');
*/
