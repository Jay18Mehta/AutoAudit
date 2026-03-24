# Compliance Guard

Production-oriented Python CLI that scans a repository for **SOC2**, **HIPAA**, and **ISO 27001**–style issues using **Google Gemini**, and emits **JSON**, **Markdown**, and **Rich** terminal summaries. The layout is split into **scanner**, **indexing**, **LLM**, **compliance**, **reporting**, **RAG (future)**, and **CLI** packages so you can swap models, add standards, or plug in **FAISS/Chroma** later.

## Requirements

- Python **3.11+**
- A **Gemini API key** ([Google AI Studio](https://aistudio.google.com/apikey))

## Setup

```bash
cd /path/to/project
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
```

If editable install fails to create the `compliance` script (some Windows permission setups), run the CLI as a module:

```bash
set PYTHONPATH=src
python -m compliance_guard scan ./path/to/repo
```

## Usage

**Scan (analyze + write reports):**

```bash
compliance scan ./my-repo
# or: python -m compliance_guard scan ./my-repo
```

Outputs under `<repo>/.compliance_guard/`:

- `scan_result.json` — full structured report
- `report.md` — human-readable Markdown

Options:

- `--redact` / `--no-redact` — mask emails, long tokens, and obvious `password=` / `api_key=` assignments before calling Gemini (default: **on**)
- `--model` / `-m` — override `GEMINI_MODEL`
- `--concurrency` / `-c` — parallel file analyses (default: 3)

**Report (reprint last scan summary):**

```bash
compliance report ./my-repo
```

**Ask (RAG-style Q&A, keyword retrieval today; embeddings + vector DB later):**

```bash
compliance ask ./my-repo "Where is JWT verified?"
```

## Security behavior

- **Never scanned as text:** `.env*`, `.pem`, `.key`, and other key/certificate extensions (see `scanner/exclusions.py`).
- **Redaction:** optional masking of emails, long token-like strings, and common secret assignments before LLM calls.
- **Large files:** skipped over **5 MB** (configurable via `MAX_FILE_BYTES`).

## Architecture (high level)

| Package        | Role |
|----------------|------|
| `scanner/`     | Recursive walk, ignore rules, binary heuristic |
| `indexing/`    | `FileIndexEntry`, `RepositoryIndex` |
| `llm/`         | `LLMClient` + `GeminiClient` (JSON + plain text) |
| `compliance/`  | Prompting, parsing, `RepositoryComplianceReport` |
| `reporting/`   | JSON / Markdown / Rich tables |
| `rag/`         | Chunking, embedding pipeline stub, context builder, `CodebaseQAService` |
| `cli/`         | Typer commands |

## Tests

```bash
set PYTHONPATH=src
python -m pytest tests -q
```

## Notes

- The `google-generativeai` package may show a deprecation notice; migrating to `google.genai` is a future follow-up without changing your package boundaries (`llm/` stays the seam).
