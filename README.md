# Smart Inventory Firaza

MVP prototype for Dicoding Capstone DB15-I033. Built with Streamlit, SQLite, scikit-learn, FastAPI, and optional Gemini API.

## Requirements
- Windows 10/11
- Python 3.10–3.12 recommended
- Internet connection for installing packages; Gemini API key is optional

## Quick start (Windows)
1. Install Python from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract this ZIP into a normal folder, e.g. `C:\Capstone\smart-inventory-firaza`.
3. Double-click `run_app.bat`. First launch installs dependencies and opens the Streamlit app.
4. The database is created automatically as `inventory.db`; demo materials and clearly-labelled synthetic usage records are seeded once.

## Run REST API
After setup, open a second Command Prompt in the project folder and run:
```bat
.venv\Scripts\activate
python -m uvicorn api:app --reload
```
Open http://127.0.0.1:8000/docs for interactive API documentation.

## Enable Gemini (optional)
1. Copy `.env.example` to `.env`.
2. Replace `your_gemini_api_key_here` with your own key. Keep `.env` private; it is excluded from Git.
3. Restart the app. Without a key, the app uses a deterministic local summary fallback and labels it clearly.

## Pages
- Dashboard: stock overview and material status.
- Materials: add, edit, and delete material master data.
- Stock Transactions: stock-in, stock-out, stock opname, and history.
- AI Inventory Summary: Gemini summary or transparent fallback.
- Model Evaluation: train/test evaluation and confusion matrix.

## Data and evaluation notes
All initial material and usage data are synthetic demo data. ML training labels are generated from an explicit rule using stock level, minimum stock, usage, and supplier lead time. Test metrics therefore measure how well the model reproduces that simulated rule, not verified performance on Firaza's real operations.

## Generate CSV exports
```bat
.venv\Scripts\activate
python generate_data.py
```

## Run tests
```bat
.venv\Scripts\activate
python -m pytest -q
```

## Gemini reliability and API-key safety
- The Gemini integration uses a bounded request timeout (15 seconds) and one explicit retry for temporary server/network failures.
- If Gemini remains unavailable, the app immediately shows the deterministic local fallback with a human-readable reason; inventory and ML features remain usable.
- Successful Gemini summaries are cached in memory for five minutes for identical inventory data. Failed responses are not cached.
- Set `GEMINI_MODEL` in your private `.env` file. The starter value is `gemini-3.8-flash`; use a model currently available to your API key. After running `run_app.bat` once, run `test_gemini.bat` to test the configured connection without displaying the API key.
- Never share `.env`, screenshots containing API keys, or commit secrets to Git. If a key is exposed, revoke it in Google AI Studio and create a replacement.
