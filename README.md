# 🔍 Job Hunter System

A **resume-driven job scraping system** that automatically finds relevant jobs from multiple Indian job portals, scores them against your profile, removes duplicates, and sends notifications via Telegram.

Built for personal use to **maximize interview opportunities within 30 days**.

## ✨ Features

- **Multi-source scraping** — Wellfound, Indeed India, Naukri, Cutshort
- **Rule-based scoring** — Jobs ranked by relevance to your profile (AI/ML, Python, Django, React)
- **Smart filtering** — Relaxed filters to maximize opportunities (experience ≤ 3 years)
- **Deduplication** — SQLite-backed URL tracking ensures you never see the same job twice
- **Telegram notifications** — Batched, formatted messages sent directly to your phone
- **Scheduled execution** — Runs every 2 hours automatically via APScheduler
- **Fault-tolerant** — One scraper failing never stops the others

## 🏗️ Architecture

```
main.py → scheduler → processor → scrapers (4 sources)
                                 → filter (experience check)
                                 → scorer (rule-based ranking)
                                 → database (SQLite dedup)
                                 → notifier (Telegram)
```

### Scoring System

| Condition                                         | Points             |
| ------------------------------------------------- | ------------------ |
| Title matches AI/ML roles                         | +100               |
| Title matches backend/SDE roles                   | +70                |
| Title matches fullstack roles                     | +50                |
| AI keywords in description (langchain, rag, etc.) | +30 each (max 120) |
| Python in description                             | +20                |
| Django in description                             | +20                |
| React / TypeScript                                | +15 each           |
| AWS / Docker                                      | +10 each           |
| Database skills                                   | +10 each           |
| Remote location                                   | +15                |
| India-based city                                  | +5                 |

### Filtering Rules

Jobs are **kept** if ANY of:

- Experience requirement ≤ 3 years
- No experience mentioned
- Title matches target role
- ≥ 2 matching skills found

Jobs are **rejected** only if experience > 3 years AND no matching role/skills.

### Scraper getting blocked?

- Increase `REQUEST_DELAY` in `config.py`
- Sites may update their HTML — check `logs/app.log` for selector errors
- The system will continue running even if one scraper fails

### No jobs found?

- Check `logs/app.log` for detailed scraper output
- Verify search terms in `config.py`
- Try running a single scraper manually for debugging
