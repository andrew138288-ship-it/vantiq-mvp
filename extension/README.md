# VANTIQ Chrome Extension

Manifest V3 Chrome extension with a side panel connected to the VANTIQ production API.

## Load in desktop Chrome
1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Select **Load unpacked**.
4. Choose this `extension` directory.
5. Open WhatsApp Web in a tab, then open the VANTIQ side panel.

## Build an installable ZIP
From the repository root, run:

```sh
python extension/package.py
```

The package is written to `dist/VANTIQ-Chrome-Extension-0.1.0.zip`. The ZIP contains the extension runtime files at its root, so extract it and choose the extracted folder with **Load unpacked**. GitHub Actions also publishes the ZIP as the `vantiq-chrome-extension` workflow artifact for 14 days after each successful CI run.

## Current capabilities
- Sign in and select a workspace when an account belongs to multiple workspaces.
- List and create tenant-scoped customer records.
- Import up to the latest 40 readable text messages from the currently open WhatsApp conversation only after the user clicks the import control.
- Review/edit imported context and explicitly confirm authorization before analysis.
- Preserve customer vs salesperson message directions when sending context to the API.
- Display two sales strategies, VANTIQ's selected strategy, the suggested reply, and pre-send checks.
- Copy the suggested reply; the user must review and manually send it.

## Privacy and safety boundaries
- The adapter reads only the currently visible conversation panel after an explicit user action.
- It does not access cookies, local storage, credentials, contact lists, hidden APIs, or background conversations.
- No automated message sending or bulk messaging is implemented.
- If the WhatsApp DOM structure changes or the visible message selector cannot be found, import fails closed and asks the user to retry after checking the page.
- Only share conversation content the user is authorized to process.

## Development checks
Run extension unit tests with Node.js 22 or later:

```sh
node --test extension/tests/*.test.mjs
```

The workflow also checks JavaScript syntax, validates the Manifest V3 permissions and entry points, builds the ZIP, and runs backend checks.
