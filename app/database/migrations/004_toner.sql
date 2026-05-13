-- Migración 004: Tóner (lecturas y catálogo)

-- Tabla de lecturas de tóner
CREATE TABLE IF NOT EXISTS toner_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    captured_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    
    -- Niveles raw (pueden ser porcentaje o absoluto según printer.toner_unit_type)
    black_level_raw INTEGER,
    black_max_raw INTEGER,
    cyan_level_raw INTEGER,
    cyan_max_raw INTEGER,
    magenta_level_raw INTEGER,
    magenta_max_raw INTEGER,
    yellow_level_raw INTEGER,
    yellow_max_raw INTEGER,
    
    -- Niveles normalizados a porcentaje (siempre 0-100)
    black_pct REAL GENERATED ALWAYS AS (
        CASE WHEN black_max_raw > 0 THEN black_level_raw * 100.0 / black_max_raw ELSE NULL END
    ) STORED,
    cyan_pct REAL GENERATED ALWAYS AS (
        CASE WHEN cyan_max_raw > 0 THEN cyan_level_raw * 100.0 / cyan_max_raw ELSE NULL END
    ) STORED,
    magenta_pct REAL GENERATED ALWAYS AS (
        CASE WHEN magenta_max_raw > 0 THEN magenta_level_raw * 100.0 / magenta_max_raw ELSE NULL END
    ) STORED,
    yellow_pct REAL GENERATED ALWAYS AS (
        CASE WHEN yellow_max_raw > 0 THEN yellow_level_raw * 100.0 / yellow_max_raw ELSE NULL END
    ) STORED
);

CREATE INDEX IF NOT EXISTS idx_toner_printer_date ON toner_readings(printer_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_toner_date ON toner_readings(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_toner_black_low ON toner_readings(black_pct) WHERE black_pct < 20;
CREATE INDEX IF NOT EXISTS idx_toner_cyan_low ON toner_readings(cyan_pct) WHERE cyan_pct < 20;
CREATE INDEX IF NOT EXISTS idx_toner_magenta_low ON toner_readings(magenta_pct) WHERE magenta_pct < 20;
CREATE INDEX IF NOT EXISTS idx_toner_yellow_low ON toner_readings(yellow_pct) WHERE yellow_pct < 20;

-- Catálogo de cartuchos de tóner
CREATE TABLE IF NOT EXISTS toner_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL,
    color TEXT CHECK(color IN ('black', 'cyan', 'magenta', 'yellow', 'waste')) NOT NULL,
    yield_pages INTEGER NOT NULL,
    compatible_printers TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('004');
