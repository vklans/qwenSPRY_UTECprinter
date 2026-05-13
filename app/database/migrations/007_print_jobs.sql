-- Migración 007: Log de impresiones y auditoría

-- Tabla de trabajos de impresión (log manual/importado)
CREATE TABLE IF NOT EXISTS print_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printed_at TEXT NOT NULL,
    username TEXT NOT NULL,
    department TEXT,
    printer_id INTEGER REFERENCES printers(id),
    pages_total INTEGER NOT NULL,
    pages_bn INTEGER NOT NULL DEFAULT 0,
    pages_color INTEGER NOT NULL DEFAULT 0,
    document_name TEXT,
    cost_center TEXT,
    
    imported_from_file INTEGER DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_printjobs_user ON print_jobs(username);
CREATE INDEX IF NOT EXISTS idx_printjobs_date ON print_jobs(printed_at DESC);
CREATE INDEX IF NOT EXISTS idx_printjobs_printer ON print_jobs(printer_id);

-- Tabla de auditoría
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    ip_address TEXT,
    details TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_table ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_log(created_at DESC);

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('007');
