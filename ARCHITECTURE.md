# Architecture

```text
GDELT ─────────────┐
Google News RSS ───┤
Bluesky ───────────┤
NewsAPI (optional) ┤
YouTube (optional) ┤──> Collector + normalization + baseline NLP
X (optional) ──────┘                    │
                                        ├──> Netlify Database / Postgres
                                        │      fallback: Netlify Blobs
                                        │
                                        ├──> 30-minute scheduled collection
                                        ├──> Telegram high-risk alert (optional)
                                        │
                                        └──> Dashboard API
                                                 │
                                                 ├── Executive KPIs
                                                 ├── Sentiment velocity
                                                 ├── Issue / narrative radar
                                                 ├── Early warning
                                                 ├── Source share
                                                 ├── Mention stream
                                                 └── AI Executive Brief
```

Sentiment classification is a deterministic Indonesian baseline with negation and basic sarcasm handling. The AI brief is context-only and does not invent facts beyond dashboard data.
