-- Migración 001: Tablas core (users, locations, printers, system_config)

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT CHECK(role IN ('superadmin', 'admin', 'operator', 'viewer')) NOT NULL,
    email TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    last_login_at TEXT,
    last_login_ip TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Tabla de ubicaciones
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    building TEXT,
    floor TEXT,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_locations_active ON locations(is_active);

-- Tabla de impresoras
CREATE TABLE IF NOT EXISTS printers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    brand TEXT CHECK(brand IN ('RICOH', 'KYOCERA', 'OTHER')) NOT NULL,
    model TEXT,
    serial_number TEXT,
    profile TEXT CHECK(profile IN ('mono_total', 'ricoh_color', 'kyocera_mono')) NOT NULL,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    
    -- Configuración SNMP
    snmp_community TEXT DEFAULT 'public',
    snmp_version TEXT DEFAULT 'v2c',
    
    -- Configuración Papel
    monitor_paper INTEGER DEFAULT 1,
    paper_capacity INTEGER DEFAULT 500,
    paper_tray_index REAL DEFAULT 1.1,
    
    -- Configuración Tóner
    monitor_toner INTEGER DEFAULT 1,
    toner_unit_type TEXT CHECK(toner_unit_type IN ('percent', 'absolute')) DEFAULT 'percent',
    
    -- Estado
    status TEXT CHECK(status IN ('active', 'maintenance', 'retired', 'offline')) DEFAULT 'active',
    is_capture_active INTEGER DEFAULT 1,
    
    notes TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_printers_location ON printers(location_id);
CREATE INDEX IF NOT EXISTS idx_printers_status ON printers(status);
CREATE INDEX IF NOT EXISTS idx_printers_capture ON printers(is_capture_active);

-- Tabla de configuración del sistema
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_by INTEGER REFERENCES users(id)
);

-- Configuración por defecto
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
('collectors.counters.interval_hours', '8', 'Horas entre capturas de contómetros'),
('collectors.paper.interval_seconds', '60', 'Segundos entre capturas de papel'),
('collectors.paper.fast_interval_seconds', '15', 'Intervalo rápido cuando hay alertas'),
('collectors.toner.interval_hours', '4', 'Horas entre capturas de tóner'),
('alerts.paper.low_threshold_percent', '20', '% para alerta LOW'),
('alerts.paper.critical_threshold_percent', '10', '% para alerta CRITICAL'),
('alerts.toner.low_threshold_percent', '20', '% para alerta tóner bajo'),
('alerts.toner.critical_threshold_percent', '10', '% para alerta tóner crítico'),
('retention.paper_readings_days', '90', 'Días de histórico de lecturas de papel'),
('retention.notifications_days', '180', 'Días de histórico de notificaciones cerradas'),
('exports.include_zero_consumption', '0', 'Incluir días con consumo 0 en exports'),
('gdrive.enabled', '0', 'Habilitar subida automática a Google Drive'),
('gdrive.folder_id', '', 'ID de carpeta en Google Drive'),
('gdrive.service_account_key', '', 'Path a credencial de servicio');

-- Tabla de control de migraciones
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

INSERT OR IGNORE INTO schema_migrations (version) VALUES ('001');
