# VANTIQ Chrome Extension

This is a Manifest V3 bootstrap shell with a side panel and backend health check.

## Load in desktop Chrome
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select **Load unpacked**.
4. Choose this `extension` directory.

## Current limitations
- No WhatsApp DOM extraction is enabled.
- No customer or contact scraping.
- No automated sending.
- The backend health check targets `http://localhost:8000/health`.

A future WhatsApp adapter must require an explicit user action, be versioned and tested against supported UI states, and fail closed when page structure is uncertain.
