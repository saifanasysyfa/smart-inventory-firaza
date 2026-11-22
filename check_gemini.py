"""Safe connectivity check for the configured Gemini API key/model."""

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

if not api_key or api_key == "your_gemini_api_key_here":
    print("FAILED: GEMINI_API_KEY is missing. Add a valid key to your local .env file.")
    raise SystemExit(1)

try:
    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=15_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    response = client.models.generate_content(
        model=model,
        contents="Reply with exactly: Gemini connection successful.",
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=40,
        ),
    )
    if not response.text:
        print("FAILED: Gemini returned an empty response.")
        raise SystemExit(1)
    print(f"SUCCESS: {model} responded successfully.")
    print("Response:", response.text.strip())
except Exception as exc:
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    print(f"FAILED: model={model}; error_type={type(exc).__name__}; status={status or 'unknown'}")
    message = str(exc).lower()
    if status == 503 or "503" in message:
        print("Meaning: Gemini service is temporarily unavailable/high demand. Retry later or test another listed model.")
    elif status == 429 or "429" in message:
        print("Meaning: API quota or rate limit was reached. Check usage and quota in Google AI Studio.")
    elif status in (401, 403) or "401" in message or "403" in message:
        print("Meaning: API key authentication or permission failed. Check the key and API access.")
    elif status == 404 or "404" in message:
        print("Meaning: This model is not available for this API request. Choose a model listed by your API key.")
    else:
        print("Meaning: Check internet connectivity and the error category above.")
    raise SystemExit(1)
