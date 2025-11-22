#!/bin/bash
# Script de mantenimiento del proyecto ENCI
# Uso: ./scripts/maintenance.sh [comando]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv/bin/python"
MANAGE="\"$PYTHON\" \"$PROJECT_ROOT/manage.py\""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para limpiar caché
clean_cache() {
    print_info "Limpiando archivos de caché Python..."
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyo" -delete 2>/dev/null || true
    print_info "✅ Caché limpiada"
}

# Función para verificar el proyecto
check_project() {
    print_info "Ejecutando verificación de Django..."
    eval $MANAGE check
    print_info "✅ Verificación completada"
}

# Función para verificar migraciones
check_migrations() {
    print_info "Verificando migraciones pendientes..."
    eval $MANAGE makemigrations --dry-run --verbosity 1
    print_info "✅ Verificación de migraciones completada"
}

# Función para ejecutar tests
run_tests() {
    print_info "Ejecutando tests..."
    eval $MANAGE test --verbosity 2
    print_info "✅ Tests completados"
}

# Función para verificar deployment
check_deploy() {
    print_warn "Verificando configuración de deployment..."
    eval $MANAGE check --deploy
}

# Función para recolectar archivos estáticos
collect_static() {
    print_info "Recolectando archivos estáticos..."
    eval $MANAGE collectstatic --noinput
    print_info "✅ Archivos estáticos recolectados"
}

# Función para mostrar ayuda
show_help() {
    cat << EOF
Script de mantenimiento del proyecto ENCI

Uso: $0 [comando]

Comandos disponibles:
  clean       - Limpiar archivos de caché Python
  check       - Verificar configuración del proyecto
  migrations  - Verificar migraciones pendientes
  test        - Ejecutar tests del proyecto
  deploy      - Verificar configuración de deployment
  static      - Recolectar archivos estáticos
  all         - Ejecutar todas las verificaciones
  help        - Mostrar esta ayuda

Ejemplos:
  $0 clean
  $0 check
  $0 all
EOF
}

# Función para ejecutar todas las verificaciones
run_all() {
    print_info "=== Ejecutando todas las verificaciones ==="
    clean_cache
    echo ""
    check_project
    echo ""
    check_migrations
    echo ""
    print_info "=== Todas las verificaciones completadas ==="
}

# Main
case "${1:-help}" in
    clean)
        clean_cache
        ;;
    check)
        check_project
        ;;
    migrations)
        check_migrations
        ;;
    test)
        run_tests
        ;;
    deploy)
        check_deploy
        ;;
    static)
        collect_static
        ;;
    all)
        run_all
        ;;
    help|*)
        show_help
        ;;
esac
