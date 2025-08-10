# Manufacturing ERP API Documentation

## Overview

The Manufacturing ERP API provides comprehensive endpoints for inventory management, demand forecasting, supply chain optimization, and alert management. Built with FastAPI for high performance and automatic documentation.

**Base URL:** `http://localhost:8000`  
**API Version:** 2.0.0  
**Authentication:** Bearer token (configured per deployment)

## Table of Contents

1. [Health Check Endpoints](#health-check-endpoints)
2. [Forecasting Endpoints](#forecasting-endpoints)
3. [Inventory Management](#inventory-management)
4. [Supply Chain](#supply-chain)
5. [Reporting](#reporting)
6. [Alert Management](#alert-management)
7. [Database Schema](#database-schema)
8. [Error Codes](#error-codes)

---

## Health Check Endpoints

### GET /api/health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-08T16:30:00Z",
  "version": "2.0.0"
}
```

### GET /api/ready
Check if system is ready to handle requests.

**Response:**
```json
{
  "ready": true,
  "data_loaded": true,
  "ml_available": true,
  "timestamp": "2025-08-08T16:30:00Z"
}
```

---

## Forecasting Endpoints

### POST /api/forecast/demand
Generate demand forecast for products.

**Request Body:**
```json
{
  "product_id": "PROD-001",
  "forecast_type": "90_day",
  "confidence_level": 0.95,
  "include_seasonality": true
}
```

**Parameters:**
- `product_id` (optional): Specific product to forecast
- `forecast_type`: One of ["daily", "weekly", "monthly", "90_day"]
- `confidence_level`: Float between 0.5 and 0.99
- `include_seasonality`: Boolean

**Response:**
```json
{
  "forecast_id": "FCT-20250808163000",
  "product_id": "PROD-001",
  "forecasts": [
    {
      "date": "2025-08-09",
      "forecast": 150.5,
      "lower_bound": 120.0,
      "upper_bound": 181.0,
      "confidence_interval": "[120, 181]"
    }
  ],
  "summary": {
    "total_forecasted_demand": 13545.0,
    "average_daily_demand": 150.5,
    "peak_demand_day": "2025-09-15",
    "minimum_demand_day": "2025-10-01",
    "demand_variability": "12.3%",
    "recommended_safety_stock": 225
  },
  "model_used": "Prophet",
  "accuracy_metrics": {
    "mape": 8.5,
    "rmse": 12.3
  },
  "created_at": "2025-08-08T16:30:00Z"
}
```

### GET /api/forecast/anomalies
Detect demand anomalies in historical data.

**Query Parameters:**
- `lookback_days`: Integer (7-365), default 30
- `threshold_std`: Float (1.0-4.0), default 2.5

**Response:**
```json
{
  "status": "success",
  "anomalies": [
    {
      "date": "2025-07-15",
      "actual": 450,
      "expected": 150,
      "deviation": 3.2,
      "type": "spike",
      "severity": "high"
    }
  ],
  "total_found": 5,
  "lookback_days": 30,
  "threshold_std": 2.5
}
```

---

## Inventory Management

### POST /api/inventory/stockout-alerts
Generate stockout risk alerts for inventory items.

**Request Body:**
```json
{
  "threshold_days": 7,
  "severity_threshold": "medium",
  "products": ["PROD-001", "PROD-002"]
}
```

**Response:**
```json
{
  "alert_id": "ALT-20250808163000",
  "alerts": [
    {
      "product_id": "PROD-001",
      "product_name": "Widget A",
      "risk_level": "critical",
      "probability": 0.92,
      "days_until_stockout": 3,
      "current_stock": 50,
      "daily_consumption": 20,
      "recommended_action": "Immediate reorder required",
      "recommended_order_qty": 500
    }
  ],
  "total_alerts": 15,
  "critical_count": 3,
  "high_count": 5,
  "medium_count": 7,
  "low_count": 0
}
```

### POST /api/inventory/optimize
Optimize inventory levels using various strategies.

**Request Body:**
```json
{
  "optimization_type": "eoq",
  "seasonality_factor": 1.2,
  "include_recommendations": true
}
```

**Parameters:**
- `optimization_type`: One of ["eoq", "abc", "safety_stock"]
- `seasonality_factor`: Float (0.1-3.0)
- `include_recommendations`: Boolean

**Response:**
```json
{
  "optimization_type": "eoq",
  "results": [
    {
      "product": "PROD-001",
      "current_stock": 100,
      "eoq": 450,
      "reorder_point": 150,
      "safety_stock": 75,
      "adjusted_demand": 180,
      "recommendation": "ACTION: Place order now - at reorder point"
    }
  ],
  "seasonality_factor": 1.2,
  "recommendations_included": true
}
```

---

## Supply Chain

### POST /api/supply-chain/risk-assessment
Assess supplier risk scores.

**Request Body:**
```json
{
  "supplier_ids": ["SUP-001", "SUP-002"],
  "include_alternatives": true,
  "risk_threshold": 70.0
}
```

**Response:**
```json
{
  "suppliers_evaluated": 12,
  "risk_scores": [
    {
      "supplier": "SUP-001",
      "supplier_name": "ABC Textiles",
      "risk_score": 82.5,
      "risk_classification": "HIGH",
      "risk_factors": {
        "delivery_performance": 65,
        "quality_score": 78,
        "financial_stability": 85,
        "geographic_risk": 90
      },
      "mitigation_strategy": "Diversify with alternative suppliers",
      "alternatives": ["SUP-005", "SUP-008"]
    }
  ],
  "high_risk_count": 3,
  "threshold": 70.0,
  "timestamp": "2025-08-08T16:30:00Z"
}
```

---

## Reporting

### GET /api/reports/kpis
Get comprehensive KPIs.

**Response:**
```json
{
  "kpis": {
    "inventory": {
      "total_value": 1250000.00,
      "turnover_ratio": 8.2,
      "stockout_rate": 2.1,
      "carrying_cost": 125000.00
    },
    "supply_chain": {
      "otif_rate": 94.5,
      "lead_time_average": 7.2,
      "supplier_performance": 88.3
    },
    "forecast": {
      "accuracy_mape": 8.5,
      "bias": 1.2,
      "tracking_signal": 0.95
    },
    "production": {
      "capacity_utilization": 78.5,
      "oee": 68.2,
      "defect_rate": 1.8
    }
  },
  "generated_at": "2025-08-08T16:30:00Z"
}
```

---

## Alert Management

### Creating Alerts

Alerts are automatically created by the system based on configured rules and thresholds. The AlertManager handles multi-channel notifications.

**Alert Types:**
- `stockout`: Inventory stockout predictions
- `low_inventory`: Low stock warnings
- `forecast_anomaly`: Unusual demand patterns
- `supplier_risk`: High supplier risk scores
- `quality_issue`: Quality control failures
- `system_error`: System operational issues

**Alert Priorities:**
- `critical`: Immediate action required
- `high`: Urgent attention needed
- `medium`: Should be addressed soon
- `low`: Informational

**Notification Channels:**
- Email: For high and critical alerts
- SMS: For critical alerts only
- Dashboard: All alerts
- Webhook: Custom integrations
- Slack: Team notifications

---

## Database Schema

### forecast_results Table
Stores ML-generated demand forecasts.

| Column | Type | Description |
|--------|------|-------------|
| forecast_id | TEXT | Unique forecast identifier |
| product_id | TEXT | Product being forecasted |
| forecast_date | TIMESTAMP | When forecast was generated |
| predicted_demand | REAL | Forecasted demand value |
| confidence_level | REAL | Confidence level (0-1) |
| model_used | TEXT | ML model used |

### shortage_alerts Table
Tracks inventory shortage predictions.

| Column | Type | Description |
|--------|------|-------------|
| alert_id | TEXT | Unique alert identifier |
| product_id | TEXT | Product at risk |
| severity | TEXT | Alert severity level |
| stockout_probability | REAL | Probability of stockout (0-1) |
| days_until_stockout | INTEGER | Predicted days to stockout |
| recommended_action | TEXT | Suggested action |

---

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Rate Limiting

API requests are limited to:
- 1000 requests per hour per API key
- 100 concurrent connections
- 10 MB maximum request size

## Authentication

Include Bearer token in Authorization header:
```
Authorization: Bearer <your-api-token>
```

## Interactive Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## SDK Support

Official SDKs available for:
- Python: `pip install manufacturing-erp-sdk`
- JavaScript/TypeScript: `npm install @manufacturing-erp/sdk`
- Go: `go get github.com/manufacturing-erp/go-sdk`

## Support

For API support and issues:
- Email: api-support@manufacturing-erp.com
- Documentation: https://docs.manufacturing-erp.com
- Status Page: https://status.manufacturing-erp.com