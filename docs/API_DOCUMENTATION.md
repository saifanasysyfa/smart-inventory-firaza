# REST API Documentation

Base URL (local): `http://127.0.0.1:8000`

## GET /health
Returns service status.

## POST /predict
Request JSON:
```json
{
  "current_stock": 5,
  "minimum_stock": 10,
  "usage_7d": 4,
  "usage_30d": 20,
  "lead_time_days": 5
}
```
Returns `status`, `confidence`, and estimated `days_of_cover`.

## GET /inventory/predictions
Returns a list of material names/SKUs and their current predicted stock status.

Interactive schema and try-it-out interface are available at `/docs`.
