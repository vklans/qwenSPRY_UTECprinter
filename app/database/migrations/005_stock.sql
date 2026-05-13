-- Migración 005: Stock (ubicaciones y movimientos)

-- Tabla de ubicaciones de stock
CREATE TABLE IF NOT EXISTS stock_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    type TEXT CHECK(type IN ('warehouse_main', 'warehouse_it', 'office', 'printer')) NOT NULL,
    parent_id INTEGER REFERENCES stock_locations(id) ON DELETE SET NULL,
    printer_id INTEGER REFERENCES printers(id) ON DELETE CASCADE,
    description TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_stock_type ON stock_locations(type);
CREATE INDEX IF NOT EXISTS idx_stock_parent ON stock_locations(parent_id);

-- Tabla de movimientos de stock (papel)
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_type TEXT CHECK(movement_type IN (
        'purchase_in',
        'transfer',
        'allocation',
        'printer_refill',
        'consumption_auto',
        'adjustment'
    )) NOT NULL,
    
    from_location_id INTEGER REFERENCES stock_locations(id),
    to_location_id INTEGER REFERENCES stock_locations(id),
    
    quantity_packs INTEGER NOT NULL,
    quantity_sheets INTEGER NOT NULL GENERATED ALWAYS AS (quantity_packs * 500) STORED,
    
    reference_number TEXT,
    printer_id INTEGER REFERENCES printers(id),
    related_reading_id INTEGER REFERENCES paper_readings(id),
    
    notes TEXT,
    performed_by INTEGER NOT NULL REFERENCES users(id),
    performed_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_stock_from ON stock_movements(from_location_id);
CREATE INDEX IF NOT EXISTS idx_stock_to ON stock_movements(to_location_id);
CREATE INDEX IF NOT EXISTS idx_stock_type ON stock_movements(movement_type);
CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_movements(performed_at DESC);

-- Trigger para validar saldo en INSERT
DROP TRIGGER IF EXISTS validate_stock_balance;
CREATE TRIGGER validate_stock_balance BEFORE INSERT ON stock_movements
BEGIN
    SELECT CASE
        WHEN NEW.from_location_id IS NOT NULL AND (
            SELECT COALESCE(SUM(quantity_sheets), 0)
            FROM stock_movements
            WHERE to_location_id = NEW.from_location_id
        ) - (
            SELECT COALESCE(SUM(quantity_sheets), 0)
            FROM stock_movements
            WHERE from_location_id = NEW.from_location_id
        ) < NEW.quantity_sheets
        THEN RAISE(ABORT, 'Saldo insuficiente en ubicación origen')
    END;
END;

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('005');
