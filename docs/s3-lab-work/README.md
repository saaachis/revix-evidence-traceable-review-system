# S3: Code Review and Lab Work

Due 2 October 2026. Two documents are handed in and presented; everything else
in here is the working material they were built from.

## What is submitted

| File | Sheets | What it is |
|---|---|---|
| **`group 5 - s3 code review & lab work.pdf`** | 13 | The document presented in the one-to-one. Cover, contents, then codebase, frameworks, code quality and non-functional requirements, and a last sheet of commands to run live |
| **`detailed non-functional-requirements.pdf`** | 8 | The full audit behind the NFR section. Opened only if he asks for the working |

Both are generated, not hand-edited. Regenerate with
`pwsh scripts/build-submission-docs.ps1`.

## What backs them up

`work/` holds the sources and the longer documents. Show these only if asked
for detail on a specific point.

| File | When you would open it |
|---|---|
| `work/00-presentation.html` / `.pdf` | The source of the submitted document. The HTML version is the one to open on screen, since its links work |
| `work/03-code-review-report.md` | The full Radon and Xenon working: every file's grade, the complexity distribution, the refactor before and after, and why mutation testing was left out |
| `work/01-lab-work-submission.md` | The long-form written submission, organised the same way as the presentation |
| `work/02-lab-work-speaking-script.md` | Internal only. What to say, sheet by sheet, and the questions to expect |

## Elsewhere in the repository

| Path | Why it matters here |
|---|---|
| [`docs/adr/`](../adr/) | The nine architecture decision records. The artefact for the frameworks section |
| [`work/non-functional-requirements.md`](work/non-functional-requirements.md) | Source of the detailed NFR PDF, and the full audit of all nine categories |
| [`docs/proposal.md`](../proposal.md) | The original specification the work is measured against |
| `tests/test_nfr.py` | The thirteen tests that assert the non-functional guarantees rather than describing them |

## Reproducing the numbers

Every figure in both documents comes from a command, and sheet 13 lists them.
The short version:

```bash
uv run radon mi packages/revix_core/src pipeline/src apps/api/src -s
uv run radon cc packages/revix_core/src pipeline/src apps/api/src -a -s -nC
uv run xenon --max-absolute D --max-modules B --max-average A \
  packages/revix_core/src pipeline/src apps/api/src
uv run pytest --cov --cov-report=term
```
