-- Migración 008: Índices optimizados y vistas adicionales

-- Índices adicionales para rendimiento
CREATE INDEX IF NOT EXISTS idx_printers_brand ON printers(brand);
CREATE INDEX IF NOT EXISTS idx_printers_profile ON printers(profile);

-- Vista para saldo de stock por ubicación
CREATE VIEW IF NOT EXISTS stock_balances AS
SELECT 
    sl.id as location_id,
    sl.name as location_name,
    sl.type as location_type,
    COALESCE(SUM(CASE WHEN sm.to_location_id = sl.id THEN sm.quantity_sheets ELSE 0 END), 0) -
    COALESCE(SUM(CASE WHEN sm.from_location_id = sl.id THEN sm.quantity_sheets ELSE 0 END), 0) as balance_sheets,
    COALESCE(SUM(CASE WHEN sm.to_location_id = sl.id THEN sm.quantity_packs ELSE 0 END), 0) -
    COALESCE(SUM(CASE WHEN sm.from_location_id = sl.id THEN sm.quantity_packs ELSE 0 END), 0) as balance_packs
FROM stock_locations sl
LEFT JOIN stock_movements sm ON (sm.to_location_id = sl.id OR sm.from_location_id = sl.id)
WHERE sl.is_active = 1
GROUP BY sl.id, sl.name, sl.type;

-- Vista para notificaciones activas agrupadas por tipo
CREATE VIEW IF NOT EXISTS active_notifications_summary AS
SELECT 
    notification_type,
    severity,
    COUNT(*) as count,
    GROUP_CONCAT(DISTINCT printer_id) as printer_ids
FROM notifications
WHERE is_active = 1 AND is_auto_resolved = 0
GROUP BY notification_type, severity;

-- Control de migraciones
INSERT OR IGNORE INTO schema_migrations (version) VALUES ('008');
