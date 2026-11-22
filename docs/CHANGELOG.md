# Changelog

## Reliability update
- Added a 15-second Gemini request timeout and one bounded retry for transient 5xx/network failures.
- Added clearer fallback messages for missing API key, invalid model, authentication, quota, and temporary provider outages.
- Added five-minute in-process caching for successful summaries only.
- Updated the Windows launcher to avoid upgrading pip and reinstalling all dependencies on every application start.
- Added automated tests for fallback, retry, cache, and non-retryable model errors.
