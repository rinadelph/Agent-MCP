-- Manufacturing ERP Database Schema
-- Enhanced tables for forecast results and shortage alerts
-- Version: 1.0
-- Date: 2025-08-08

-- ============================================
-- FORECAST RESULTS TABLE
-- ============================================
-- Stores ML-generated demand forecasts and predictions
CREATE TABLE IF NOT EXISTS forecast_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_id TEXT UNIQUE NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    forecast_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    forecast_type TEXT CHECK(forecast_type IN ('daily', 'weekly', 'monthly', '90_day')),
    model_used TEXT,
    
    -- Forecast values
    forecast_period_start DATE NOT NULL,
    forecast_period_end DATE NOT NULL,
    predicted_demand REAL NOT NULL,
    lower_bound REAL,
    upper_bound REAL,
    confidence_level REAL DEFAULT 0.95,
    
    -- Model metrics
    accuracy_score REAL,
    mape REAL,  -- Mean Absolute Percentage Error
    rmse REAL,  -- Root Mean Square Error
    
    -- Seasonality factors
    seasonality_factor REAL DEFAULT 1.0,
    trend_direction TEXT CHECK(trend_direction IN ('up', 'down', 'stable')),
    
    -- Business context
    current_inventory REAL,
    safety_stock REAL,
    reorder_point REAL,
    recommended_order_qty REAL,
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_forecast_product ON forecast_results(product_id);
CREATE INDEX idx_forecast_date ON forecast_results(forecast_date);
CREATE INDEX idx_forecast_period ON forecast_results(forecast_period_start, forecast_period_end);
CREATE INDEX idx_forecast_active ON forecast_results(is_active);

-- ============================================
-- SHORTAGE ALERTS TABLE
-- ============================================
-- Tracks inventory shortage predictions and alerts
CREATE TABLE IF NOT EXISTS shortage_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT UNIQUE NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    alert_type TEXT CHECK(alert_type IN ('stockout', 'low_stock', 'reorder', 'critical')),
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Alert details
    current_stock REAL NOT NULL,
    daily_consumption_rate REAL,
    days_until_stockout INTEGER,
    predicted_stockout_date DATE,
    
    -- Thresholds
    safety_stock_level REAL,
    reorder_point REAL,
    minimum_stock_level REAL,
    
    -- Risk metrics
    stockout_probability REAL CHECK(stockout_probability >= 0 AND stockout_probability <= 1),
    risk_score REAL,
    confidence_level REAL DEFAULT 0.95,
    
    -- Recommendation
    recommended_action TEXT,
    recommended_order_qty REAL,
    recommended_order_date DATE,
    estimated_lead_time INTEGER,
    
    -- Alert status
    alert_status TEXT CHECK(alert_status IN ('new', 'acknowledged', 'in_progress', 'resolved', 'dismissed')),
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMP,
    resolved_by TEXT,
    resolved_at TIMESTAMP,
    
    -- Notification tracking
    notification_sent BOOLEAN DEFAULT 0,
    notification_channels TEXT,  -- JSON array of channels (email, sms, dashboard)
    notification_sent_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX idx_alert_product ON shortage_alerts(product_id);
CREATE INDEX idx_alert_type ON shortage_alerts(alert_type);
CREATE INDEX idx_alert_severity ON shortage_alerts(severity);
CREATE INDEX idx_alert_status ON shortage_alerts(alert_status);
CREATE INDEX idx_alert_active ON shortage_alerts(is_active);
CREATE INDEX idx_alert_stockout_date ON shortage_alerts(predicted_stockout_date);

-- ============================================
-- FORECAST HISTORY TABLE
-- ============================================
-- Tracks historical accuracy of forecasts for model improvement
CREATE TABLE IF NOT EXISTS forecast_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    forecast_date DATE NOT NULL,
    predicted_value REAL NOT NULL,
    actual_value REAL,
    error_percentage REAL,
    model_used TEXT,
    
    FOREIGN KEY (forecast_id) REFERENCES forecast_results(forecast_id)
);

CREATE INDEX idx_history_forecast ON forecast_history(forecast_id);
CREATE INDEX idx_history_product ON forecast_history(product_id);
CREATE INDEX idx_history_date ON forecast_history(forecast_date);

-- ============================================
-- ALERT HISTORY TABLE
-- ============================================
-- Tracks alert effectiveness and response times
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    action_taken TEXT,
    action_by TEXT,
    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    outcome TEXT,
    response_time_hours REAL,
    
    FOREIGN KEY (alert_id) REFERENCES shortage_alerts(alert_id)
);

CREATE INDEX idx_alert_history_id ON alert_history(alert_id);
CREATE INDEX idx_alert_history_date ON alert_history(action_date);

-- ============================================
-- VIEWS FOR REPORTING
-- ============================================

-- Active alerts view
CREATE VIEW IF NOT EXISTS v_active_alerts AS
SELECT 
    sa.*,
    fr.predicted_demand,
    fr.confidence_level as forecast_confidence
FROM shortage_alerts sa
LEFT JOIN forecast_results fr ON sa.product_id = fr.product_id 
    AND fr.is_active = 1
WHERE sa.is_active = 1 
    AND sa.alert_status NOT IN ('resolved', 'dismissed')
ORDER BY sa.severity DESC, sa.predicted_stockout_date ASC;

-- Forecast accuracy view
CREATE VIEW IF NOT EXISTS v_forecast_accuracy AS
SELECT 
    fh.product_id,
    fh.model_used,
    COUNT(*) as total_forecasts,
    AVG(ABS(fh.error_percentage)) as avg_error,
    MIN(ABS(fh.error_percentage)) as best_error,
    MAX(ABS(fh.error_percentage)) as worst_error
FROM forecast_history fh
WHERE fh.actual_value IS NOT NULL
GROUP BY fh.product_id, fh.model_used;

-- ============================================
-- TRIGGERS FOR DATA INTEGRITY
-- ============================================

-- Update timestamp trigger for forecast_results
CREATE TRIGGER IF NOT EXISTS update_forecast_timestamp 
AFTER UPDATE ON forecast_results
BEGIN
    UPDATE forecast_results 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Update timestamp trigger for shortage_alerts
CREATE TRIGGER IF NOT EXISTS update_alert_timestamp 
AFTER UPDATE ON shortage_alerts
BEGIN
    UPDATE shortage_alerts 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;

-- Auto-expire old alerts
CREATE TRIGGER IF NOT EXISTS auto_expire_alerts
AFTER INSERT ON shortage_alerts
BEGIN
    UPDATE shortage_alerts
    SET is_active = 0
    WHERE expires_at < CURRENT_TIMESTAMP
        AND is_active = 1;
END;