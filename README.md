# 🔍 Job Hunter AI

A **resume-driven job scraping system** that automatically finds relevant jobs from multiple Indian job portals, scores them against your profile, removes duplicates, and sends notifications via Telegram.

Built for personal use to **maximize interview opportunities within 30 days**.

## ✨ Features

- **Multi-source scraping** — LinkedIn, Wellfound, Instahyre
- **Rule-based scoring** — Jobs ranked by relevance to your profile (AI/ML, Python, Django, React)
- **Smart filtering** — Relaxed filters to maximize opportunities (experience ≤ 3 years)
- **Deduplication** — PostgreSQL-backed URL tracking ensures you never see the same job twice
- **Telegram notifications** — Batched, formatted messages sent directly to your phone
- **Cloud Ready** — Dockerized and configured for automatic deployment on Render with Aiven Postgres.

## 🏗️ Architecture

```
main.py → scheduler → processor → scrapers (LinkedIn, Wellfound, Instahyre)
                                 → filter (experience check)
                                 → scorer (rule-based ranking)
                                 → database (PostgreSQL dedup)
                                 → notifier (Telegram)
```

## 🚀 Deployment (Render)

1. Connect this repository to a **Render Web Service**.
2. Select **Docker** as the environment.
3. Add your Environment Variables:
   - `BOT_TOKEN`: Your Telegram Bot Token
   - `CHAT_ID`: Your Telegram Group Chat ID
   - `DATABASE_URL`: Your Aiven PostgreSQL connection string

## ⚖️ License & Copyright

**Copyright (c) 2026. All Rights Reserved.**

This code is provided for educational and review purposes only. You may not copy, modify, distribute, sell, or run this code for your own commercial or personal use without explicit permission from the author.

---
*Note: Indeed, Naukri, and Cutshort scrapers are currently disabled by default due to strict Cloudflare anti-bot protections (403 Forbidden).*
