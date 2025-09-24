AWS Frontend Quickstart (Angular)

Goal
- Host the Angular SPA on AWS with SPA routing and proxy `/api` and `/mcp` to your backend.

What you have
- App root: `hedge-agent/`
- Build: `npm run build:prod`
- Output: `dist/hedge-accounting-sfx`
- Backend (current): `https://3-91-170-95.nip.io` (update to your API domain when ready)

Option A: AWS Amplify Hosting (fastest)
1) Push repo to GitHub and connect in Amplify Hosting.
2) App settings
   - Monorepo base directory: `hedge-agent`
   - Build command: `npm ci && npm run build:prod`
   - Artifact directory: `dist/hedge-accounting-sfx`
3) Rewrites and redirects
   - { Source: "/api/<*>", Target: "https://3-91-170-95.nip.io/api/<*>", Type: 200 }
   - { Source: "/mcp/<*>", Target: "https://3-91-170-95.nip.io/mcp/<*>", Type: 200 }
   - { Source: "/<*>", Target: "/index.html", Type: 200, Condition: SPA fallback }
     Tip: Use regex source `</^[^.]+$/>` if you want to exclude asset files from the SPA fallback.
4) Save and deploy. Connect your custom domain if needed.

Option B: S3 + CloudFront (classic AWS)
Prereqs
- AWS CLI configured; Node 18+ locally.

Build and upload
```bash
cd hedge-agent
npm ci
npm run build:prod
aws s3 mb s3://your-frontend-bucket
aws s3 sync dist/hedge-accounting-sfx/ s3://your-frontend-bucket/ --delete
```

S3 static website + SPA fallback
- Enable static website hosting; set Index and Error document to `index.html`.
- Or, keep bucket private and serve via CloudFront with an Origin Access Control.

CloudFront distribution (two origins)
- Origin 1: S3 bucket (the SPA)
- Origin 2: Backend API (e.g., `3-91-170-95.nip.io` or your ALB/API Gateway)
- Behaviors
  - Default behavior → Origin 1 (S3). Cache static, GET/HEAD.
  - Path `/api/*` → Origin 2. Allow GET/POST/OPTIONS; forward headers/cookies as your API requires.
  - Path `/mcp/*` → Origin 2. Same as above.
- SPA routing
  - Add custom error responses on the S3 origin: map 403/404 to `/index.html` with HTTP 200.

Example minimal CLI for the static site-only path
```bash
# If you only need static hosting (no proxying), you can start with this:
aws cloudfront create-distribution \
  --origin-domain-name your-frontend-bucket.s3-website-<region>.amazonaws.com \
  --default-root-object index.html
```
Then evolve to two origins and path-based behaviors in the console or via IaC (CDK/CloudFormation) when ready.

Security notes
- Do not ship secrets in the frontend. `src/index.html` currently embeds a Supabase anon key; prefer moving to backend and calling through `/api`.
- Configure CORS on the backend for the CloudFront/Amplify domain.

Troubleshooting
- 403/404 on deep links → SPA fallback not configured; set S3 Error document to `index.html` or CloudFront custom error responses.
- API calls blocked → add `/api/*` and `/mcp/*` behaviors to CloudFront or rewrites in Amplify; verify HTTPS on the backend.
- Mixed content errors → ensure backend is HTTPS and target host matches your rules.

