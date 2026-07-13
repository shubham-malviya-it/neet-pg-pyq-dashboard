# NEET-PG PYQ Analytics

An interactive, self-contained dashboard that analyses **16 years of NEET-PG previous-year question papers (2010–2025)** and pairs them with the official **2026 syllabus**.

**Live:** https://neet-pg-pyq-dashboard.vercel.app

## What it does

Every extractable question from the previous papers is parsed and classified into one of the 19 MBBS subjects (and a sub-topic within each) using a weighted medical-keyword classifier. The dashboard turns that into:

- **Subject weightage** — ranked share of questions per subject, with an all-years vs. recent-3-papers toggle.
- **Trends** — question mix over time by curriculum block, and a subject × year heatmap.
- **Movers** — subjects gaining or losing weight in recent papers.
- **Topic drill-down** — expand any subject for its sub-topic breakdown and year-by-year trend.
- **Question browser** — search all ~3,300 parsed questions by subject, topic, year, or keyword.
- **Papers library** — direct links to all question papers and solutions (2010–2025).
- **2026 syllabus explorer** — all 19 subjects across the three curriculum blocks, linked to the official NBEMS Information Bulletin.
- **2026 predictions** — an external 180 high-yield-topic forecast (priority + past-repetition per topic), plus a diverging chart comparing the forecast's subject emphasis against the actual historical PYQ share.

## Files

| File | Purpose |
|------|---------|
| `index.html` | The dashboard — a single self-contained page (inline CSS/JS, no CDN). |
| `data.js` | Generated analysis consumed by the dashboard. |
| `build_analysis.py` | The pipeline: extracts questions from the PDFs, classifies subject + topic, emits `data.js`. |
| `NEET-PG-2025-Recall-Questions.md` | Student-recall question set used for 2025 (the exam is memory-based). |
| `NEET-PG-2026-Predicted-Topics.pdf` | External 180 high-yield-topic forecast, parsed into the Predictions tab. |
| `NEET-PG-*.pdf` | Question papers and solutions, 2010–2025, plus the 2026 bulletin. |

## Regenerating the data

```bash
pip install PyPDF2
python build_analysis.py      # rewrites data.js from the PDFs + recall set
```

## Method & caveats

Subject/topic percentages are **directional estimates** from keyword classification — NBEMS does not publish an official subject-wise breakdown. Notes on specific years:

- **2015** was never released publicly.
- **2016** is a solved compilation, kept in the library but excluded from the subject stats.
- **2025** uses a ~200-question student recall set (the exam is memory-based).

## Deploying

Static site — deploys as-is on Vercel:

```bash
vercel deploy --prod
```
