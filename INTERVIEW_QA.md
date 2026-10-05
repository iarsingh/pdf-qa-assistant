# pdf-qa-assistant — interview questions and answers

[README](README.md) · [Project architecture](PROJECT_ARCHITECTURE.md)

Answers below use this repository’s files and implementation. They distinguish existing behavior from suggested extensions; source links let you verify each walkthrough.

## 1. What problem does pdf-qa-assistant address, and what can you demonstrate?

PDFs in `corpus/` and PDFs uploaded at runtime are split into pages and then sentences. A question is answered with the best matching sentence and a citation such as `runbook.pdf p.2`. A question that shares fewer than two meaningful words with every sentence is refused. No hosted model is called.

I would demonstrate the linked implementation or examples and distinguish that evidence from any planned production features. Start with [`README.md`](README.md).

## 2. How is this repository organized?

- [`src/pdfqa/main.py`](src/pdfqa/main.py): Implementation or supporting configuration.
- [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py): Implementation or supporting configuration.
- [`src/pdfqa/answer.py`](src/pdfqa/answer.py): Implementation or supporting configuration.
- [`requirements.txt`](requirements.txt): Implementation or supporting configuration.
- [`src/pdfqa/__init__.py`](src/pdfqa/__init__.py): Implementation or supporting configuration.
- [`tests/test_pdfqa.py`](tests/test_pdfqa.py): Executable checks and regression examples.
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml): GitHub Actions job definitions.
- [`README.md`](README.md): Project explanations or operating notes.

[PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) contains the component diagram and the implementation walkthrough.

## 3. Can you walk through `build` and explain the decision it makes?

The main walkthrough here is `build(pages, compress=False)` in [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py#L10). Return bytes of a valid PDF with one text line per list item on each page.

```python
def build(pages, compress=False):
    """Return bytes of a valid PDF with one text line per list item on each page."""
    count = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, lines in enumerate(pages):
        page_id, content_id = 4 + 2 * index, 5 + 2 * index
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        body = "BT /F1 11 Tf 72 720 Td 14 TL\n" + "".join(f"({escape(line)}) Tj T*\n" for line in lines) + "ET"
        data = body.encode("latin-1")
        extra = ""
        if compress:
            data = zlib.compress(data)
```

This is an excerpt; follow the source link for the rest of the branches.

The implementation calls `' '.join`, `''.join`, `body.encode`, `bytearray`, `bytes`, `enumerate`, `escape`, `f'<< /Length {len(data)}{extra} >>\nstream\n'.encode`, `f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>'.encode`. In an interview, trace those calls in execution order using a fixture input.

## 4. What responsibility does `add_document` have?

`add_document(name, content_base64)` is defined in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L77).

Its return expressions include:

- `{'name': name, 'pages': len(pages)}`

It uses `DocumentError`, `NAME.match`, `base64.b64decode`, `data.startswith`, `extract_pages`, `isinstance`, `len`, `load_corpus`. This is the code path I would compare against the caller to explain responsibility boundaries.

## 5. What input validation and failure behavior are implemented?

Explicit failure paths include:

- `DocumentError('name must look like runbook.pdf: lowercase letters, digits, dash, underscore')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L79).
- `DocumentError('name is taken by a corpus document')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L81).
- `DocumentError(f'at most {MAX_DOCUMENTS} uploaded documents')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L83).
- `DocumentError(f'PDF is larger than {MAX_BYTES} bytes')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L89).
- `DocumentError('file does not start with %PDF-')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L91).
- `DocumentError('no extractable text; a scanned PDF needs OCR first')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L94).
- `DocumentError('question is empty')` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py#L122).

I would test both the condition that reaches each exception and the caller that translates it. An explicit raise does not mean every malformed input or dependency failure is handled.

## 6. Which test would you use to demonstrate correctness?

[`tests/test_pdfqa.py`](tests/test_pdfqa.py#L24) contains `test_answers_from_the_pdf_and_refuses_an_unrelated_question`:

```python
def test_answers_from_the_pdf_and_refuses_an_unrelated_question():
    hit = client.post("/ask", json={"question": "What does the platform refuse in production?"}).json()
    assert hit["answered"] is True
    assert "production" in hit["answer"]
    assert hit["citation"].endswith("p.1")
    miss = client.post("/ask", json={"question": "What is the cafeteria menu?"}).json()
    assert miss["answered"] is False
    assert miss["citation"] is None
```

This is a concrete regression example from the repository. Its assertions establish that case; they do not establish behavior for every input or under production load.

## 7. What HTTP interface does the code expose?

- `GET /healthz` → `healthz` in [`src/pdfqa/main.py`](src/pdfqa/main.py#L9).
- `POST /ask` → `post_ask` in [`src/pdfqa/main.py`](src/pdfqa/main.py#L14).
- `GET /documents` → `list_documents` in [`src/pdfqa/main.py`](src/pdfqa/main.py#L22).
- `POST /documents` → `post_document` in [`src/pdfqa/main.py`](src/pdfqa/main.py#L27).

These are literal decorators. Application/router prefixes, authentication, and middleware must be checked in the corresponding setup code.

## 8. Where does state live, and what happens with multiple workers?

Module-level containers include `STOP`, `ESCAPES`, `UPLOADED` in [`src/pdfqa/answer.py`](src/pdfqa/answer.py); `HANDBOOK` in [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py).

These containers belong to a Python process. Inspect which are constant fixtures and which are mutated. Mutable process state needs an explicit shared-storage or synchronization strategy before multiple workers can provide consistent behavior.

## 9. How would another engineer reproduce your walkthrough?

Start from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands follow repository manifests; environment setup and command results still need to be checked on the target machine.

## 10. What does automation verify, and what does it not prove?

Inspect [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for triggers, permissions, and job commands. I would name the checks that those definitions run and show the latest run separately. A workflow definition alone does not establish a successful deployment, security review, or production SLO.

## 11. How would you present this project in a Forward Deployed Engineer interview?

Start with the user and operational problem described in [`README.md`](README.md). Explain one constraint that changes the implementation, show the linked code or example, and walk through a success case and a failure case. Agree on a measurable acceptance criterion before expanding the solution, and leave a handoff with data boundaries and rollback ownership. Any proposed production or business metric should be identified as a target until measured.

## 12. What is the input-to-output contract of `build`?

In [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py#L10), `build(pages, compress=False)` receives the inputs. The function computes these intermediate values:

- `count = len(pages)`
- `kids = ' '.join((f'{4 + 2 * i} 0 R' for i in range(count)))`
- `objects = {1: b'<< /Type /Catalog /Pages 2 0 R >>', 2: f'<< /Type /Pages /Kids [{kids}] /Count {count} >>'.encode(), 3: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'}`
- `out = bytearray(b'%PDF-1.4\n')`
- `offsets = {}`
- `xref = len(out)`

Its result is defined by:

- `bytes(out)`

## 13. Which decision rules or boundary conditions should an interviewer challenge?

The implementation in [`src/pdfqa/pdfgen.py`](src/pdfqa/pdfgen.py#L10) branches on:

- `compress`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.
