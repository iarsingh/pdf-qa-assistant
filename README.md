# PDF Question-Answering Assistant

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
