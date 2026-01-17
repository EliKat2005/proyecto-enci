-- Script para crear tablas de Kardex y Cierre de Periodos manualmente
-- Uso: python manage.py dbshell < scripts/create_kardex_tables.sql

-- 1. Tabla de Cierre de Periodos
CREATE TABLE IF NOT EXISTS contabilidad_empresa_cierre_periodo (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    empresa_id BIGINT NOT NULL,
    periodo INT NOT NULL,
    fecha_cierre DATE NOT NULL,
    asiento_cierre_id BIGINT NULL,
    cerrado_por_id INT NULL,
    fecha_registro DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    utilidad_neta DECIMAL(20, 2) NOT NULL DEFAULT 0,
    total_ingresos DECIMAL(20, 2) NOT NULL DEFAULT 0,
    total_costos DECIMAL(20, 2) NOT NULL DEFAULT 0,
    total_gastos DECIMAL(20, 2) NOT NULL DEFAULT 0,
    bloqueado TINYINT(1) NOT NULL DEFAULT 1,
    notas LONGTEXT,
    UNIQUE KEY unique_empresa_periodo (empresa_id, periodo),
    KEY idx_empresa_periodo (empresa_id, periodo),
    KEY idx_fecha_cierre (fecha_cierre),
    CONSTRAINT fk_cierre_empresa FOREIGN KEY (empresa_id)
        REFERENCES contabilidad_empresa(id) ON DELETE CASCADE,
    CONSTRAINT fk_cierre_asiento FOREIGN KEY (asiento_cierre_id)
        REFERENCES contabilidad_empresaasiento(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cierre_usuario FOREIGN KEY (cerrado_por_id)
        REFERENCES auth_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tabla de Productos de Inventario
CREATE TABLE IF NOT EXISTS contabilidad_producto_inventario (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    empresa_id BIGINT NOT NULL,
    sku VARCHAR(50) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    descripcion LONGTEXT,
    categoria VARCHAR(100),
    unidad_medida VARCHAR(20) NOT NULL,
    metodo_valoracion VARCHAR(20) NOT NULL DEFAULT 'PROMEDIO',
    stock_minimo DECIMAL(15, 3) NOT NULL DEFAULT 0,
    stock_maximo DECIMAL(15, 3) NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    cuenta_inventario_id BIGINT NOT NULL,
    cuenta_costo_venta_id BIGINT NULL,
    creado_por_id INT NULL,
    fecha_creacion DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    fecha_actualizacion DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY unique_empresa_sku (empresa_id, sku),
    KEY idx_empresa_sku (empresa_id, sku),
    KEY idx_empresa_activo (empresa_id, activo),
    KEY idx_categoria (categoria),
    KEY idx_sku (sku),
    CONSTRAINT fk_producto_empresa FOREIGN KEY (empresa_id)
        REFERENCES contabilidad_empresa(id) ON DELETE CASCADE,
    CONSTRAINT fk_producto_cuenta_inv FOREIGN KEY (cuenta_inventario_id)
        REFERENCES contabilidad_empresa_plandecuentas(id) ON DELETE RESTRICT,
    CONSTRAINT fk_producto_cuenta_costo FOREIGN KEY (cuenta_costo_venta_id)
        REFERENCES contabilidad_empresa_plandecuentas(id) ON DELETE RESTRICT,
    CONSTRAINT fk_producto_creador FOREIGN KEY (creado_por_id)
        REFERENCES auth_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabla de Movimientos Kardex
CREATE TABLE IF NOT EXISTS contabilidad_movimiento_kardex (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    producto_id BIGINT NOT NULL,
    fecha DATE NOT NULL,
    tipo_movimiento VARCHAR(20) NOT NULL,
    cantidad DECIMAL(15, 3) NOT NULL,
    costo_unitario DECIMAL(15, 6) NOT NULL,
    valor_total_movimiento DECIMAL(20, 2) NOT NULL,
    cantidad_saldo DECIMAL(15, 3) NOT NULL,
    costo_promedio DECIMAL(15, 6) NOT NULL,
    valor_total_saldo DECIMAL(20, 2) NOT NULL,
    asiento_id BIGINT NULL,
    documento_referencia VARCHAR(100),
    tercero_id BIGINT NULL,
    observaciones LONGTEXT,
    creado_por_id INT NULL,
    fecha_registro DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_producto_fecha (producto_id, fecha),
    KEY idx_producto_fecha_desc (producto_id, fecha DESC, id DESC),
    KEY idx_tipo_movimiento (tipo_movimiento),
    KEY idx_fecha (fecha),
    CONSTRAINT fk_kardex_producto FOREIGN KEY (producto_id)
        REFERENCES contabilidad_producto_inventario(id) ON DELETE RESTRICT,
    CONSTRAINT fk_kardex_asiento FOREIGN KEY (asiento_id)
        REFERENCES contabilidad_empresaasiento(id) ON DELETE RESTRICT,
    CONSTRAINT fk_kardex_tercero FOREIGN KEY (tercero_id)
        REFERENCES contabilidad_empresa_tercero(id) ON DELETE SET NULL,
    CONSTRAINT fk_kardex_creador FOREIGN KEY (creado_por_id)
        REFERENCES auth_user(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Confirmar creación
SELECT 'Tablas creadas exitosamente:' AS Status;
SHOW TABLES LIKE 'contabilidad_%cierre%';
SHOW TABLES LIKE 'contabilidad_%producto%';
SHOW TABLES LIKE 'contabilidad_%kardex%';
