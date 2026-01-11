/**
 * Analytics.js - Funciones para cargar y visualizar métricas financieras
 */

// Utilidad para obtener el CSRF token
function getCookie(name) {
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

const csrftoken = getCookie('csrftoken');

/**
 * Carga las métricas financieras de una empresa
 */
async function cargarMetricas(empresaId) {
    const loadingEl = document.getElementById('loading-metricas');
    const errorEl = document.getElementById('error-metricas');

    try {
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (errorEl) errorEl.classList.add('hidden');

        const response = await fetch(`/contabilidad/api/ml/analytics/metricas/${empresaId}/`);

        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Actualizar KPIs
        actualizarKPIs(data.metricas);

        // Crear gráficos
        crearGraficoRadar(data.metricas);
        crearGraficoBarras(data.metricas);

        if (loadingEl) loadingEl.classList.add('hidden');
    } catch (error) {
        console.error('Error cargando métricas:', error);
        if (loadingEl) loadingEl.classList.add('hidden');
        if (errorEl) {
            errorEl.classList.remove('hidden');
            errorEl.textContent = `Error: ${error.message}`;
        }
    }
}

/**
 * Actualiza los KPIs en las tarjetas
 */
function actualizarKPIs(metricas) {
    // Liquidez
    const liquidezEl = document.getElementById('liquidez-value');
    if (liquidezEl) {
        liquidezEl.textContent = metricas.liquidez_corriente?.toFixed(2) || 'N/A';
        liquidezEl.classList.add('text-blue-600', 'dark:text-blue-400');
    }

    // Rentabilidad
    const rentabilidadEl = document.getElementById('rentabilidad-value');
    if (rentabilidadEl) {
        const valor = metricas.rentabilidad_activos ? (metricas.rentabilidad_activos * 100).toFixed(2) : 'N/A';
        rentabilidadEl.textContent = valor !== 'N/A' ? `${valor}%` : 'N/A';
        rentabilidadEl.classList.add('text-green-600', 'dark:text-green-400');
    }

    // Endeudamiento
    const endeudamientoEl = document.getElementById('endeudamiento-value');
    if (endeudamientoEl) {
        const valor = metricas.endeudamiento_total ? (metricas.endeudamiento_total * 100).toFixed(2) : 'N/A';
        endeudamientoEl.textContent = valor !== 'N/A' ? `${valor}%` : 'N/A';
        endeudamientoEl.classList.add('text-orange-600', 'dark:text-orange-400');
    }

    // Margen Neto
    const margenEl = document.getElementById('margen-value');
    if (margenEl) {
        const valor = metricas.margen_neto ? (metricas.margen_neto * 100).toFixed(2) : 'N/A';
        margenEl.textContent = valor !== 'N/A' ? `${valor}%` : 'N/A';
        margenEl.classList.add('text-purple-600', 'dark:text-purple-400');
    }
}

/**
 * Crea un gráfico de radar para las métricas
 */
function crearGraficoRadar(metricas) {
    const ctx = document.getElementById('metricsRadarChart');
    if (!ctx) return;

    // Destruir gráfico anterior si existe
    if (window.radarChart) {
        window.radarChart.destroy();
    }

    window.radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Liquidez Corriente', 'Rentabilidad ROA', 'Rentabilidad ROE', 'Endeudamiento', 'Rotación Activos'],
            datasets: [{
                label: 'Métricas Financieras',
                data: [
                    metricas.liquidez_corriente || 0,
                    (metricas.rentabilidad_activos || 0) * 100,
                    (metricas.rentabilidad_patrimonio || 0) * 100,
                    (metricas.endeudamiento_total || 0) * 100,
                    (metricas.rotacion_activos || 0)
                ],
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 2,
                pointBackgroundColor: 'rgb(59, 130, 246)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(59, 130, 246)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        backdropColor: 'transparent'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += context.parsed.r.toFixed(2);
                            return label;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Crea un gráfico de barras para las métricas
 */
function crearGraficoBarras(metricas) {
    const ctx = document.getElementById('metricsBarChart');
    if (!ctx) return;

    // Destruir gráfico anterior si existe
    if (window.barChart) {
        window.barChart.destroy();
    }

    window.barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Liquidez', 'ROA', 'ROE', 'Margen Neto', 'Rotación'],
            datasets: [{
                label: 'Valores (%)',
                data: [
                    metricas.liquidez_corriente || 0,
                    (metricas.rentabilidad_activos || 0) * 100,
                    (metricas.rentabilidad_patrimonio || 0) * 100,
                    (metricas.margen_neto || 0) * 100,
                    (metricas.rotacion_activos || 0)
                ],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(139, 92, 246, 0.8)',
                    'rgba(236, 72, 153, 0.8)'
                ],
                borderColor: [
                    'rgb(59, 130, 246)',
                    'rgb(16, 185, 129)',
                    'rgb(245, 158, 11)',
                    'rgb(139, 92, 246)',
                    'rgb(236, 72, 153)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Carga las tendencias de ingresos y gastos
 */
async function cargarTendencias(empresaId, meses = 12) {
    const loadingEl = document.getElementById('loading-tendencias');
    const errorEl = document.getElementById('error-tendencias');

    try {
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (errorEl) errorEl.classList.add('hidden');

        const response = await fetch(`/contabilidad/api/ml/analytics/tendencias/${empresaId}/?meses=${meses}`);

        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Crear gráfico de líneas
        crearGraficoTendencias(data);

        // Actualizar resumen
        actualizarResumenTendencias(data.resumen);

        if (loadingEl) loadingEl.classList.add('hidden');
    } catch (error) {
        console.error('Error cargando tendencias:', error);
        if (loadingEl) loadingEl.classList.add('hidden');
        if (errorEl) {
            errorEl.classList.remove('hidden');
            errorEl.textContent = `Error: ${error.message}`;
        }
    }
}

/**
 * Crea gráfico de líneas para tendencias
 */
function crearGraficoTendencias(data) {
    const ctx = document.getElementById('tendenciasChart');
    if (!ctx) return;

    if (window.tendenciasChart) {
        window.tendenciasChart.destroy();
    }

    const meses = data.tendencias.map(t => t.mes);
    const ingresos = data.tendencias.map(t => t.ingresos);
    const gastos = data.tendencias.map(t => t.gastos);
    const margen = data.tendencias.map(t => t.margen);

    window.tendenciasChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: meses,
            datasets: [
                {
                    label: 'Ingresos',
                    data: ingresos,
                    borderColor: 'rgb(16, 185, 129)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Gastos',
                    data: gastos,
                    borderColor: 'rgb(239, 68, 68)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Margen',
                    data: margen,
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

/**
 * Actualiza el resumen de tendencias
 */
function actualizarResumenTendencias(resumen) {
    if (!resumen) return;

    const totalIngresosEl = document.getElementById('total-ingresos');
    if (totalIngresosEl) {
        totalIngresosEl.textContent = `$${resumen.total_ingresos?.toLocaleString() || '0'}`;
    }

    const totalGastosEl = document.getElementById('total-gastos');
    if (totalGastosEl) {
        totalGastosEl.textContent = `$${resumen.total_gastos?.toLocaleString() || '0'}`;
    }

    const margenPromedioEl = document.getElementById('margen-promedio');
    if (margenPromedioEl) {
        margenPromedioEl.textContent = `${resumen.margen_promedio?.toFixed(2) || '0'}%`;
    }
}

/**
 * Carga el top de cuentas más activas
 */
async function cargarTopCuentas(empresaId, limit = 10) {
    try {
        const response = await fetch(`/contabilidad/api/ml/analytics/top-cuentas/${empresaId}/?limit=${limit}`);

        if (!response.ok) {
            throw new Error(`Error ${response.status}`);
        }

        const data = await response.json();
        mostrarTopCuentas(data.top_cuentas);
    } catch (error) {
        console.error('Error cargando top cuentas:', error);
    }
}

/**
 * Muestra la tabla de top cuentas
 */
function mostrarTopCuentas(cuentas) {
    const tbody = document.getElementById('top-cuentas-tbody');
    if (!tbody) return;

    tbody.innerHTML = '';

    cuentas.forEach(cuenta => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 dark:hover:bg-dark-surface';
        row.innerHTML = `
            <td class="px-4 py-3 text-sm">${cuenta.ranking}</td>
            <td class="px-4 py-3 text-sm font-medium">${cuenta.cuenta_codigo}</td>
            <td class="px-4 py-3 text-sm">${cuenta.cuenta_nombre}</td>
            <td class="px-4 py-3 text-sm text-right">${cuenta.total_movimientos}</td>
            <td class="px-4 py-3 text-sm text-right">$${cuenta.total_debe.toLocaleString()}</td>
            <td class="px-4 py-3 text-sm text-right">$${cuenta.total_haber.toLocaleString()}</td>
            <td class="px-4 py-3 text-sm text-right font-medium">${cuenta.saldo_neto >= 0 ? 'Deudor' : 'Acreedor'}</td>
        `;
        tbody.appendChild(row);
    });
}

// Exportar funciones para uso global
window.cargarMetricas = cargarMetricas;
window.cargarTendencias = cargarTendencias;
window.cargarTopCuentas = cargarTopCuentas;
