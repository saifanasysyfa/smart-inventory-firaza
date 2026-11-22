# Technical Documentation — Smart Inventory Firaza

## 1. System overview
The MVP combines a Streamlit user interface, SQLite persistence, a scikit-learn stock-status classifier, a FastAPI inference service, and an optional Gemini API integration.

## 2. Data model

### materials
- `material_id`: primary key
- `sku`: unique material identifier
- `material_name`, `category`, `unit`
- `current_stock`, `minimum_stock`
- `lead_time_days`, `supplier`, `updated_at`

### transactions
- `transaction_id`: primary key
- `material_id`: foreign key to materials
- `transaction_type`: STOCK_IN, STOCK_OUT, or STOCK_OPNAME
- `quantity`, `note`, `transaction_date`

Stock rules: STOCK_IN adds quantity; STOCK_OUT subtracts quantity and cannot make stock negative; STOCK_OPNAME sets current stock to the counted quantity. All three events are stored in the transaction history.

## 3. ML design
Input features: current_stock, minimum_stock, usage_7d, usage_30d, and lead_time_days. A Random Forest classifier predicts Safe, Need Attention, or Restock Priority. Training examples and labels are synthetic. Labels are generated using a documented deterministic rule based on stock-to-minimum ratio and estimated days of stock coverage.

The evaluation uses a stratified 80/20 train/test split with a fixed random seed. Reported scores measure agreement with the synthetic labeling rule only; they are not evidence of accuracy on Firaza's real operational data.

## 4. REST API
- `GET /health`: service health check.
- `POST /predict`: classify one inventory feature record.
- `GET /inventory/predictions`: classify all seeded/current database materials.
- Interactive OpenAPI documentation: `/docs` while API server is running.

## 5. Generative AI
When GEMINI_API_KEY is configured, the application sends the current inventory analysis context to the Gemini API and asks for a factual Bahasa Indonesia summary and restock recommendations. If the key is absent or the request fails, a deterministic local fallback summary is displayed and clearly labeled.

## 6. Limitations
- No real Firaza transaction or inventory data was supplied; all initial records are synthetic.
- No marketplace sales integration is included, consistent with the approved project plan.
- The model is a proof-of-concept classifier trained on synthetic rule-generated labels.
- Recommendations must be validated by the business owner before purchasing.
