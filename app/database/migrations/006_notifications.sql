-- Migración 006: Notificaciones

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_id INTEGER NOT NULL REFERENCES printers(id) ON DELETE CASCADE,
    notification_type TEXT CHECK(notification_type IN (
        'PAPER_JAM',
        'PAPER_EMPTY',
        'PAPER_LOW',
        'PAPER_CRITICAL',
        'TONER_LOW_BLACK',
        'TONER_LOW_CYAN',
        'TONER_LOW_MAGENTA',
        'TONER_LOW_YELLOW',
        'TONER_EMPTY_BLACK',
        'TONER_EMPTY_CYAN',
        'TONER_EMPTY_MAGENTA',
        'TONER_EMPTY_YELLOW',
        'SERVICE_CALL'
    )) NOT NULL,
    
    severity TEXT CHECK(severity IN ('info', 'warning', 'critical')) NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    
    alert_code INTEGER,
    alert_description TEXT,
    
    is_active INTEGER DEFAULT 1,
    is_acknowledged INTEGER DEFAULT 0,
    acknowledged_by INTEGER REFERENCES users(id),
    acknowledged_at TEXT,
    
    is_auto_resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    resolved_by INTEGER REFERENCES users(id),
    
    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active) WHERE is_active = 1;
CREATE INDEX IF NOT EXISTS idx_notifications_printer ON notifications(printer_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('006');
