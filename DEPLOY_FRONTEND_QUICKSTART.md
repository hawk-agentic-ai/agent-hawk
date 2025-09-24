Quickstart: Deploy Angular Frontend

Overview
- App: Angular 18 app in `hedge-agent/`
- Build output: `dist/hedge-accounting-sfx`
- Backend: proxied to `https://3-91-170-95.nip.io` via `/api` and `/mcp`
- SPA routing: enabled (fallback to `index.html`)

Option A: Vercel (fastest)
1) Push this repo to GitHub (or ensure Vercel can access it).
2) In Vercel, import the project and select `hedge-agent` as the root.
3) Framework preset: Angular
4) Build command: `npm run build:prod`
5) Output directory: `dist/hedge-accounting-sfx`
6) `vercel.json` is included to:
   - Proxy `/api/*` and `/mcp/*` to `https://3-91-170-95.nip.io`
   - Enable SPA fallback routing

Option B: Netlify
1) Push to GitHub and connect repo in Netlify.
2) Base directory: `hedge-agent`
3) Build command: `npm run build:prod`
4) Publish directory: `dist/hedge-accounting-sfx`
5) `netlify.toml` is included to:
   - Proxy `/api/*` and `/mcp/*` to `https://3-91-170-95.nip.io`
   - Enable SPA fallback routing

Local Build (if you want to test)
- Requires Node 18+ and npm
- From `hedge-agent/` run:
  - `npm ci`
  - `npm run build:prod`
  - Serve locally: `npm run serve` (serves `dist/...` on port 3000)

Notes
- Angular routes start at `/hedge/dashboard` and others; SPA fallback ensures refresh works.
- The dev proxy (`proxy.conf.json`) targets the same backend for local `ng serve`.
- If you change the backend host, update `vercel.json` and `netlify.toml` rewrites.
- For GitHub Pages, you’ll need CORS on the backend and a SPA fallback (e.g., copy `index.html` to `404.html`).

