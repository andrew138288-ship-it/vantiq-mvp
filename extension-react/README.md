# VANTIQ React WhatsApp Dock

Chrome Manifest V3 extension built with TypeScript, React, and Vite.

## Build and test

```sh
npm ci
npm test
npm run build
python package.py
```

The build writes the unpacked extension to `dist/`. The ZIP package is written to the repository root `dist/VANTIQ-WhatsApp-Dock-0.2.0.zip`.

## Load in Chrome

1. For the device-test package, the API is preconfigured to `https://vantiq-mvp-production-97577cdb.up.railway.app`. For local development, start the VANTIQ FastAPI backend at `http://localhost:8000` and build without `VITE_API_BASE`.
2. Open `chrome://extensions` in desktop Chrome.
3. Enable Developer mode and choose **Load unpacked**.
4. Select this package's `dist/` folder.
5. Open WhatsApp Web; the dock appears inside the page on the right.

Set `VITE_API_BASE` at build time to change the backend origin. The corresponding host must also be listed in `manifest.json` permissions. The CI-generated installable package is configured for the isolated device-test API, not the production API.

## Privacy and safety

- No conversation is read until the user clicks **读取当前 WhatsApp 对话**.
- Only the currently open conversation is considered.
- The user can review/edit the transcript and must explicitly authorize analysis.
- Switching the WhatsApp conversation or selected customer clears prior context and consent.
- No cookies, credentials, QR codes, hidden endpoints, contact scraping, or auto-send.
- The reply is copied for human review; the user sends it manually.
