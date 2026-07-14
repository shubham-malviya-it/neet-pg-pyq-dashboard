# Rights and source audit

This file is an inventory, not a grant of rights or a legal opinion. No project-wide
license or written redistribution permission for the third-party exam, solution,
recall, syllabus, or forecast material was found in this repository on 14 July
2026. A file being publicly obtainable, educational, attributed, or present in
the repository does **not** establish permission to copy or redistribute it.

Before operating a public deployment, the maintainer should verify the owner,
original URL, applicable terms, and redistribution basis for every source below.
Remove or replace any item whose status cannot be established. Rights holders may
request correction or removal through the repository's normal issue/contact route.

## Audit inventory

| Local material | Apparent source or attribution | How the project uses it | Rights/verification status |
|---|---|---|---|
| `NEET-PG-2010` through `2014-Question-Paper.pdf` (5 files) | Not recorded in the repository | Local source for extraction; linked paper library | Owner, original URL, authenticity, and redistribution permission unknown |
| `NEET-PG-2010` through `2014-Solutions.pdf` (5 files) | Not recorded in the repository | Linked solution library; not the primary statistics source | Publisher/author and redistribution permission unknown |
| `NEET-PG-2016-Question-Paper.pdf` and `NEET-PG-2016-Answer-Key.pdf` | Not recorded; the pipeline describes 2016 as a solved compilation | Library only; 2016 is excluded from subject statistics | Publisher/author, authenticity, and redistribution permission unknown |
| `NEET-PG-2017` through `2023-Question-Paper.pdf` (7 files) | Not recorded in the repository | Local source for extraction; linked paper library | Owner, original URL, authenticity, and redistribution permission unknown |
| `NEET-PG-2017` through `2023-Solutions.pdf` (7 files) | Not recorded in the repository | Linked solution library | Publisher/author and redistribution permission unknown |
| `NEET-PG-2024-Shift-1-Question-Paper.pdf` and `NEET-PG-2024-Shift-2-Question-Paper.pdf` | Not recorded in the repository | Local sources for extraction; linked paper library | Owner, original URLs, authenticity, and redistribution permission unknown |
| `NEET-PG-2024-Shift-1-Solutions.pdf` and `NEET-PG-2024-Shift-2-Solutions.pdf` | Not recorded in the repository | Linked solution library | Publisher/author and redistribution permission unknown |
| `NEET-PG-2025-Question-Paper.pdf` and `NEET-PG-2025-Solutions.pdf` | Not recorded in the repository; described elsewhere as memory-based | Linked paper/solution library; PDF paper is superseded for analysis by the recall set | Publisher/compiler, original URLs, and redistribution permission unknown |
| `NEET-PG-2025-Recall-Questions.md` | File declares “DigiNerve (student recall compilation)” | Replaces the 2025 paper as the analysis input | Attribution is present, but authorisation, completeness, accuracy, and redistribution terms are not documented |
| `NEET-PG-2026-Information-Bulletin-Syllabus.pdf` | Filename and project text identify NBEMS; official site referenced as <https://natboard.edu.in/> | Syllabus reference and local linked bulletin | Confirm document authenticity, official source URL, and government-document reuse terms; no permission is asserted here |
| `NEET-PG-2026-NBEMS-Exam-Notice.pdf` | Filename identifies NBEMS; official site referenced as <https://natboard.edu.in/> | Local exam-notice reference | Confirm authenticity, official source URL, and reuse terms; no permission is asserted here |
| `NEET-PG-2026-Syllabus-Collegedunia.md` | Captured Collegedunia page; the file contains “© 2026 Collegedunia Web Pvt. Ltd. All Rights Reserved” and links to <https://collegedunia.com/exams/neet-pg/syllabus> | Supplemental syllabus research; excluded from deployment | Third-party copyright is expressly signalled; permission to retain or redistribute is not documented |
| `NEET-PG-2026-Predicted-Topics.pdf` | Pipeline attribution: “Dr Ganga's Master Medicine — 180 high-yield topic forecast for NEET-PG 2026” | Parsed into the dashboard's prediction view; PDF is locally linked/deployed | Ownership, original URL, forecast methodology, and redistribution permission require verification |
| `notes.js` | Described as hand-compiled revision notes; individual references are not recorded | Prediction drill-down content | Authorship and source-by-source provenance are not documented; review for copied expression and add citations where applicable |
| `data.js` and `questions.json` | Generated locally from the materials above by `build_analysis.py` | Dashboard summary and question-browser data | Generation does not erase rights in source wording; extracted questions may reproduce protected material |
| `classifier_benchmark.json` | Generated from small synthetic, manually labelled stems defined in `build_analysis.py` | Classifier smoke benchmark; explicitly not a production accuracy estimate | Project-created fixture as currently documented; check any future cases before assuming the same status |

The grouped rows above account for all 35 PDFs currently stored at the repository
root. There is no 2015 file: the project states that the paper was not publicly
released.

## Provenance recorded by the application

The year summaries in `data.js` retain local source filenames. Enhanced question
records in `questions.json` retain `src` and, when recoverable, `page` and `qnum`.
These fields document which local input produced a record; they do not prove that
the input is official, accurate, or lawfully redistributable.

Classification fields (`confidence` and `candidates`) describe the keyword
classifier's relative certainty, not medical correctness, exam authenticity, or
source reliability. Image flags identify records whose meaning may depend on
figures that text extraction cannot preserve.

## Deployment note

The current static deployment keeps PDF links local and `vercel.json` caches those
version-named files. `.vercelignore` excludes tooling, not the PDFs. That technical
choice is not a rights determination: if public redistribution is not authorised,
exclude the affected PDFs from deployment and replace local links with verified
publisher links or remove them.
