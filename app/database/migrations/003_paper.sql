-- Migración 003: Papel (lecturas y eventos)

-- Tabla de lecturas de papel
CREATE TABLE IF NOT EXISTS paper_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    captured_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    sheets_available INTEGER,
    capacity INTEGER NOT NULL,
    level_percent REAL GENERATED ALWAYS AS (sheets_available * 100.0 / capacity) STORED,
    alert_code INTEGER,
    alert_description TEXT
);

CREATE INDEX IF NOT EXISTS idx_paper_printer_date ON paper_readings(printer_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_date ON paper_readings(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_low ON paper_readings(level_percent) WHERE level_percent < 20;

-- Tabla de eventos de papel
CREATE TABLE IF NOT EXISTS paper_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    event_type TEXT CHECK(event_type IN (
        'PAPER_LOW', 
        'PAPER_CRITICAL', 
        'PAPER_EMPTY', 
        'PAPER_REFILLED',
        'PAPER_JAM'
    )) NOT NULL,
    occurred_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    previous_level INTEGER,
    new_level INTEGER,
    alert_code INTEGER,
    resolved_at TEXT,
    resolved_by INTEGER REFERENCES users(id),
    auto_resolved INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_printer ON paper_events(printer_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON paper_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_unresolved ON paper_events(resolved_at) WHERE resolved_at IS NULL;

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('003');
