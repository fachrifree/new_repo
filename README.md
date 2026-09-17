# Sentiment Command Center v2

Production-friendly media and public-opinion intelligence dashboard for BP Tapera / FLPP / housing-related monitoring.

## Live sources without API keys
- GDELT news index
- Google News RSS search
- Bluesky public AppView search

## Optional credentialed sources
- NewsAPI (`NEWSAPI_KEY`)
- YouTube Data API (`YOUTUBE_API_KEY`)
- X recent search (`X_BEARER_TOKEN`)

## Storage
The app prefers Netlify Database (managed Postgres) and automatically falls back to Netlify Blobs when Database is unavailable. This allows the dashboard to run even on a plan where managed Postgres is not enabled.

## Endpoints
- `GET /api/health`
- `GET /api/dashboard?hours=168&source=all&sentiment=all&q=`
- `POST /api/ai-brief`
- `POST /api/collect` (protected with `INTERNAL_TOKEN`)
- `scheduled-collect` every 30 minutes

## Deploy
Deploy to Netlify. The `netlify.toml`, functions, and migration are included. Netlify installs dependencies and serves `public/`.

## Required environment
- `MONITOR_QUERY`
- `STORAGE_MODE=auto`
- `ENABLE_GDELT=true`
- `ENABLE_GOOGLE_NEWS=true`
- `ENABLE_BLUESKY=true`
- `COLLECT_LIMIT=25`
- `INTERNAL_TOKEN=<secret>`

## Optional alerting
Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to enable high-risk Telegram alerts.

## AI brief
The dashboard includes an AI Brief button. It uses Netlify AI Gateway when enabled for the site, and safely falls back to statistical briefing when AI Gateway is unavailable.

## Notes
Estimated reach is explicitly an estimate when a source does not expose authoritative impression/reach data.
