# NEET-PG PYQ Analytics

An interactive static dashboard for exploring locally collected NEET-PG previous-
year papers (2010–2025), heuristic subject/topic classifications, and a 2026
syllabus and topic forecast.

**Live:** <https://neet-pg-pyq-dashboard.vercel.app>

This is an independent study aid. It is not affiliated with, endorsed by, or an
official publication of NBEMS/NBE or NMC. Do not use it as a substitute for an
official bulletin, answer key, or medical reference.

## Features

- Subject weightage, curriculum-block trends, a subject/year heatmap, and recent movers
- Subject and topic drill-downs with year-by-year counts
- Searchable question records with source provenance and classification confidence
- Local paper, solution, answer-key, notice, and syllabus links
- A third-party 2026 high-yield-topic forecast compared with historical classifications
- Extraction-quality signals and inline source-page crops for image-dependent questions

## Architecture

The application has no server-side runtime and makes no database or third-party API
requests. Vercel serves the repository's static HTML, JavaScript, and local PDFs.

| File | Role |
|---|---|
| `index.html`, `styles.css`, `app.js` | Static interface, presentation, and dashboard behaviour |
| `data.js` | Generated aggregate data assigned to `window.NEET_DATA`; deliberately excludes question text |
| `questions.json` | Generated question records, provenance, classifier diagnostics, extraction quality, and image cues |
| `classifier_benchmark.json` | Generated results for a small, manually labelled classifier smoke fixture |
| `notes.js` | Hand-compiled revision notes shown in the prediction drill-down |
| `build_analysis.py` | Extracts local inputs, classifies records, and regenerates the data artifacts |
| `requirements.txt` | Reproducible Python dependency constraint for PDF extraction |
| `vercel.json` | Static security and cache headers; PDFs remain local assets |
| `RIGHTS_AND_SOURCES.md` | Source/rights audit and unresolved verification work |
| `NEET-PG-*.pdf`, `NEET-PG-2025-Recall-Questions.md` | Local source corpus |

At build time, PDF or recall text flows through question extraction, weighted
keyword classification, topic classification, and quality/provenance annotation.
`data.js` holds compact summaries used on initial load; the browser fetches
`questions.json` for question-level views.

## Regenerating data

Python 3.9 or newer is recommended. From the repository root:

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# POSIX: source .venv/bin/activate
python -m pip install -r requirements.txt
python build_analysis.py
```

The generator rewrites `data.js`, `questions.json`, and
`classifier_benchmark.json`. Review all generated-file diffs before committing
them; changes in `PyPDF2`, source PDFs, extraction rules, keywords, or thresholds
can alter results. Do not hand-edit generated artifacts. To run just the in-memory
classifier smoke fixture without extracting PDFs:

```bash
python build_analysis.py --benchmark
```

## Data model and provenance

`data.js` contains canonical sections and subjects, per-year counts and source
inventories, aggregate subject/topic totals, denominators, and prediction data.
`questions.json` contains a metadata object and a `questions` array. Each record
keeps compact display fields (`y`, `s`, `t`, `q`, optional `a`) plus:

- `src`, `source_kind`, `page`, `qnum`, and `page_link` for traceability;
- `score`, normalized `confidence`, `margin`, `tie`, `threshold`,
  `meets_threshold`, `scores`, and `candidates` for classifier review;
- `image`, `image_cues`, `image_asset`, and crop metadata for questions likely to depend on a figure; and
- `extraction` quality, score, character/option counts, and warning flags.

Provenance identifies the **local input** from which text was extracted. It does
not certify that a paper is official, complete, accurate, or permitted for
redistribution. See [RIGHTS_AND_SOURCES.md](RIGHTS_AND_SOURCES.md) before deploying
or reusing the corpus.

## Confidence and denominators

Subject and topic labels come from weighted keyword matches, not an expert-reviewed
answer key or an NBEMS subject breakdown. Any nonzero keyword score is assigned a
subject, and every classified record receives a topic (`General` when no specific
topic rule matches). Top-score ties use the canonical subject order while retaining
the tie flag, candidates, scores, and zero separation confidence for review. A
zero-score question remains unclassified. `confidence` is a normalized classifier
signal; candidate scores and the margin expose plausible alternatives. A high
value means the configured rules separated one label more clearly—it does not mean
the label or question is medically correct. Ties, low-quality extraction, and
image-dependent questions deserve manual review.

Totals and percentages must be read with their denominator. Parsed-question totals
include unclassified records; subject statistics count classified records in the
eligible statistics years. The generated per-year denominator fields make that
distinction explicit. Never interpret a subject share as an official exam blueprint
or as the probability that a future question will appear.

## Known limitations

- **2015:** no paper is present; the project records it as not publicly released.
- **2016:** the available solved compilation has unsuitable option ordering, so it
  remains in the library but is excluded from subject/trend statistics.
- **2025:** analysis uses an attributed student-recall compilation in place of the
  small memory-based PDF; recall wording and coverage are inherently uncertain.
- PDF text order, OCR, multi-column layout, and symbols can be lost or corrupted.
  PDF-backed visual questions include an automatically anchored source-page crop;
  the 2025 recall source is text-only, so its referenced visuals cannot be recovered.
- Keyword classifiers can confuse overlapping specialties, negation, answer
  explanations, and sparse stems. Topic labels inherit the subject-label error.
- Answer letters are included only when a recognizable marker exists and are not
  independently verified.
- The 2026 prediction material is a third-party forecast, not an official forecast
  or a promise of exam coverage.
- Historical source origin and redistribution rights are incomplete. The rights
  audit makes no assertion that repository or public deployment is authorised.

## Testing

Run the complete integrity suite with:

```bash
python -m unittest discover -s tests -v
```

It verifies the 19-subject taxonomy, section/year sets, aggregate arithmetic,
local source existence, topic totals, question/summary reconciliation, provenance,
confidence bounds, candidate subjects, extraction diagnostics, image booleans,
benchmark arithmetic, numbered-block/page extraction, classifier coverage/tie
behaviour, topic fallback, image-cue detection, and that question text is split out of `data.js`. If a
concurrent regeneration has not created an enhanced artifact yet, its artifact-
specific class is skipped; all available summary checks still run.

## Deployment

Deploy the static files as-is:

```bash
vercel deploy --prod
```

`vercel.json` adds a restrictive static-site security policy, prevents framing,
limits browser capabilities, revalidates mutable HTML/JS/JSON/CSS, and gives the
PDFs a bounded browser/CDN cache lifetime. The PDFs are intentionally not
excluded by `.vercelignore`, so links remain local. Confirm redistribution rights
before a public deployment; caching and local hosting are technical choices, not
evidence of permission.
