/**
 * Sistema de autocompletado avanzado para búsqueda de cuentas.
 * Utiliza las APIs optimizadas de búsqueda (FASE 2).
 */

class AutocompleteSearch {
    constructor(inputElement, resultsContainer, options = {}) {
        this.input = inputElement;
        this.resultsContainer = resultsContainer;
        this.empresaId = options.empresaId || null;
        this.debounceTime = options.debounceTime || 300;
        this.minChars = options.minChars || 2;
        this.maxResults = options.maxResults || 10;
        this.onSelect = options.onSelect || (() => {});

        this.debounceTimeout = null;
        this.currentIndex = -1;
        this.suggestions = [];

        this.init();
    }

    init() {
        // Event listeners
        this.input.addEventListener('input', (e) => this.handleInput(e));
        this.input.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.input.addEventListener('blur', () => {
            // Delay para permitir click en suggestions
            setTimeout(() => this.hideSuggestions(), 200);
        });

        // Crear container de resultados si no existe
        if (!this.resultsContainer) {
            this.resultsContainer = document.createElement('div');
            this.resultsContainer.className = 'autocomplete-results';
            this.input.parentElement.appendChild(this.resultsContainer);
        }
    }

    handleInput(event) {
        const query = event.target.value.trim();

        // Limpiar timeout anterior
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }

        // Si query es muy corto, ocultar sugerencias
        if (query.length < this.minChars) {
            this.hideSuggestions();
            return;
        }

        // Debounce
        this.debounceTimeout = setTimeout(() => {
            this.fetchSuggestions(query);
        }, this.debounceTime);
    }

    async fetchSuggestions(query) {
        if (!this.empresaId) {
            console.error('No se ha especificado empresaId');
            return;
        }

        try {
            // Mostrar loading
            this.showLoading();

            const response = await fetch(`/api/ml/advanced/autocomplete/${this.empresaId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    partial_query: query,
                    limit: this.maxResults,
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.suggestions = data.suggestions || [];
            this.showSuggestions();

        } catch (error) {
            console.error('Error al obtener sugerencias:', error);
            this.showError('Error al buscar sugerencias');
        }
    }

    showSuggestions() {
        // Limpiar
        this.resultsContainer.innerHTML = '';
        this.currentIndex = -1;

        if (this.suggestions.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="autocomplete-item autocomplete-no-results">
                    <span class="text-gray-500 dark:text-gray-400">
                        No se encontraron resultados
                    </span>
                </div>
            `;
            this.resultsContainer.classList.add('show');
            return;
        }

        // Generar items
        this.suggestions.forEach((suggestion, index) => {
            const item = this.createSuggestionItem(suggestion, index);
            this.resultsContainer.appendChild(item);
        });

        this.resultsContainer.classList.add('show');
    }

    createSuggestionItem(suggestion, index) {
        const div = document.createElement('div');
        div.className = 'autocomplete-item';
        div.dataset.index = index;

        // Badge de tipo de cuenta
        const tipoBadge = this.getTipoBadge(suggestion.tipo);

        // Badge de frecuencia de uso
        const frecuenciaBadge = this.getFrecuenciaBadge(suggestion.uso_frecuencia);

        div.innerHTML = `
            <div class="flex items-center justify-between w-full">
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-mono text-sm font-medium text-gray-700 dark:text-gray-300">
                            ${suggestion.codigo}
                        </span>
                        ${tipoBadge}
                        ${frecuenciaBadge}
                    </div>
                    <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        ${suggestion.descripcion}
                    </div>
                </div>
                ${suggestion.es_auxiliar ? '<span class="ml-2 text-xs text-blue-600 dark:text-blue-400">Auxiliar</span>' : ''}
            </div>
        `;

        // Click handler
        div.addEventListener('click', () => this.selectSuggestion(suggestion));

        // Hover handler
        div.addEventListener('mouseenter', () => {
            this.setActiveIndex(index);
        });

        return div;
    }

    getTipoBadge(tipo) {
        const badges = {
            'ACTIVO': '<span class="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">Activo</span>',
            'PASIVO': '<span class="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 rounded">Pasivo</span>',
            'PATRIMONIO': '<span class="px-2 py-0.5 text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 rounded">Patrimonio</span>',
            'INGRESO': '<span class="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded">Ingreso</span>',
            'GASTO': '<span class="px-2 py-0.5 text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200 rounded">Gasto</span>',
            'COSTO': '<span class="px-2 py-0.5 text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded">Costo</span>',
        };
        return badges[tipo] || '';
    }

    getFrecuenciaBadge(frecuencia) {
        if (!frecuencia || frecuencia === 0) return '';

        let emoji = '';
        let colorClass = '';

        if (frecuencia >= 100) {
            emoji = '🔥';
            colorClass = 'text-red-600 dark:text-red-400';
        } else if (frecuencia >= 50) {
            emoji = '⭐';
            colorClass = 'text-yellow-600 dark:text-yellow-400';
        } else if (frecuencia >= 10) {
            emoji = '✨';
            colorClass = 'text-blue-600 dark:text-blue-400';
        } else {
            return '';
        }

        return `<span class="text-xs ${colorClass}" title="${frecuencia} transacciones">${emoji}</span>`;
    }

    showLoading() {
        this.resultsContainer.innerHTML = `
            <div class="autocomplete-item autocomplete-loading">
                <div class="flex items-center space-x-2">
                    <svg class="animate-spin h-4 w-4 text-gray-600 dark:text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="text-sm text-gray-600 dark:text-gray-400">Buscando...</span>
                </div>
            </div>
        `;
        this.resultsContainer.classList.add('show');
    }

    showError(message) {
        this.resultsContainer.innerHTML = `
            <div class="autocomplete-item autocomplete-error">
                <span class="text-red-600 dark:text-red-400 text-sm">
                    ⚠️ ${message}
                </span>
            </div>
        `;
        this.resultsContainer.classList.add('show');
    }

    hideSuggestions() {
        this.resultsContainer.classList.remove('show');
        this.currentIndex = -1;
    }

    handleKeyDown(event) {
        if (!this.resultsContainer.classList.contains('show')) {
            return;
        }

        const items = this.resultsContainer.querySelectorAll('.autocomplete-item:not(.autocomplete-loading):not(.autocomplete-no-results):not(.autocomplete-error)');

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.currentIndex = Math.min(this.currentIndex + 1, items.length - 1);
                this.updateActiveItem(items);
                break;

            case 'ArrowUp':
                event.preventDefault();
                this.currentIndex = Math.max(this.currentIndex - 1, -1);
                this.updateActiveItem(items);
                break;

            case 'Enter':
                event.preventDefault();
                if (this.currentIndex >= 0 && this.currentIndex < this.suggestions.length) {
                    this.selectSuggestion(this.suggestions[this.currentIndex]);
                }
                break;

            case 'Escape':
                event.preventDefault();
                this.hideSuggestions();
                break;
        }
    }

    setActiveIndex(index) {
        this.currentIndex = index;
        const items = this.resultsContainer.querySelectorAll('.autocomplete-item:not(.autocomplete-loading):not(.autocomplete-no-results):not(.autocomplete-error)');
        this.updateActiveItem(items);
    }

    updateActiveItem(items) {
        items.forEach((item, index) => {
            if (index === this.currentIndex) {
                item.classList.add('active');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('active');
            }
        });
    }

    selectSuggestion(suggestion) {
        this.input.value = `${suggestion.codigo} - ${suggestion.descripcion}`;
        this.hideSuggestions();
        this.onSelect(suggestion);
    }

    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}

// Export para uso en otros scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutocompleteSearch;
}
