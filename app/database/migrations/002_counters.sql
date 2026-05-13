-- Migración 002: Contómetros y consumo

-- Tabla de lecturas de contómetros
CREATE TABLE IF NOT EXISTS counter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    captured_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    total_impressions INTEGER NOT NULL DEFAULT 0,
    bn_impressions INTEGER NOT NULL DEFAULT 0,
    color_impressions INTEGER NOT NULL DEFAULT 0,
    
    UNIQUE(printer_id, captured_at)
);

CREATE INDEX IF NOT EXISTS idx_counter_printer_date ON counter_readings(printer_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_counter_date ON counter_readings(captured_at);

-- Vista para consumo diario
CREATE VIEW IF NOT EXISTS daily_consumption AS
SELECT 
    DATE(captured_at) as date,
    printer_id,
    MIN(total_impressions) as total_start,
    MAX(total_impressions) as total_end,
    MAX(total_impressions) - MIN(total_impressions) as daily_consumption,
    MIN(bn_impressions) as bn_start,
    MAX(bn_impressions) as bn_end,
    MAX(bn_impressions) - MIN(bn_impressions) as bn_consumption,
    MIN(color_impressions) as color_start,
    MAX(color_impressions) as color_end,
    MAX(color_impressions) - MIN(color_impressions) as color_consumption,
    COUNT(*) as reading_count
FROM counter_readings
GROUP BY DATE(captured_at), printer_id
HAVING daily_consumption > 0;

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('002');
