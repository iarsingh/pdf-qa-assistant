# PDF Question-Answering Assistant

<!-- project-guide:start -->
## Project guide

[Project architecture](PROJECT_ARCHITECTURE.md) · [Interview questions and answers](INTERVIEW_QA.md)

Use the architecture document for the component diagram, implementation boundaries, and verification entry points. The interview guide includes source-backed answers and project walkthroughs.

### Implementation map

| Component | Responsibility |
| --- | --- |
| [`src/pdfqa/main.py`](src/pdfqa/main.py) | HTTP handlers: `GET /healthz`, `POST /ask`, `GET /documents`, `POST /documents` |
| [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py) | Functions: `escape`, `build` |
| [`src/pdfqa/answer.py`](src/pdfqa/answer.py) | Functions: `unescape`, `stream_text`, `extract_pages`, `extract_pdf_text`, `load_corpus`, `documents`, `add_document` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/pdfqa/__init__.py`](src/pdfqa/__init__.py) | Implementation or supporting configuration |
| [`tests/test_pdfqa.py`](tests/test_pdfqa.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |

### Local setup and verification

From the repository root (the commands follow the checked-in manifests):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

To serve the FastAPI application locally, install the server separately if it is not already available:

```bash
python -m pip install uvicorn
PYTHONPATH=src python -m uvicorn pdfqa.main:app --reload
```

<!-- project-guide:end -->

Level: 6 — Beginner RAG

Skills: Python, PDF content streams, page-level citations, input validation, local retrieval

PDFs in `corpus/` and PDFs uploaded at runtime are split into pages and then sentences. A question is answered with the best matching sentence and a citation such as `runbook.pdf p.2`. A question that shares fewer than two meaningful words with every sentence is refused. No hosted model is called.

```bash
pip install -r requirements.txt
pytest -q
PYTHONPATH=src uvicorn pdfqa.main:app --reload
```

| Method and path | Returns |
| --- | --- |
| `POST /ask` | `answered`, `answer`, `citation`, and the top `top_k` passages (1 to 10, default 3) |
| `GET /documents` | Each document and its page count |
| `POST /documents` | Upload `{"name": "runbook.pdf", "content_base64": "..."}` |

```bash
curl -s -X POST localhost:8000/documents -H 'content-type: application/json' \
  -d "{\"name\":\"runbook.pdf\",\"content_base64\":\"$(base64 < runbook.pdf | tr -d '\n')\"}"
curl -s -X POST localhost:8000/ask -H 'content-type: application/json' -d '{"question":"How long does failover take?"}'
```

## Extraction

`pdfqa.answer.extract_pages` reads each content stream in order, inflates FlateDecode streams, and collects the strings drawn by `Tj`, `'`, `"`, and `TJ`, including escaped parentheses, backslashes, and octal codes. It is deliberately small: it does not handle custom font encodings or scanned images. A PDF with no extractable text is refused with a message saying it needs OCR.

`pdfqa.pdfgen.build` writes a valid PDF with correct cross-reference offsets. Tests use it to build fixtures, and `PYTHONPATH=src python -m pdfqa.pdfgen corpus/handbook.pdf` writes a three-page sample.

## Upload rules

- The name is lowercase letters, digits, dashes, or underscores ending in `.pdf`, and cannot replace a corpus file.
- The content must be valid base64, at most 2 MB, and start with `%PDF-`.
- At most 20 uploads are held, in memory only.

## Ops plane

Workspaces, tenant isolation, job approval, and audit live under `/v1`. Production apply is refused. See `docs/ARCHITECTURE.md`.

## Documentation checks

Project architecture, interview guides, and local source links are checked automatically on pushes and pull requests. Run the same check locally:

```bash
python3 .github/scripts/validate_project_docs.py
```

See [service improvements and local run instructions](docs/UPGRADES.md).
