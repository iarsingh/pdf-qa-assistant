from fastapi import FastAPI, HTTPException

from pdfqa.answer import DocumentError, add_document, answer, documents

app = FastAPI()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/ask")
def post_ask(body: dict):
    try:
        return answer(body.get("question"), body.get("top_k", 3))
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/documents")
def list_documents():
    return {"documents": [{"name": name, "pages": len(pages)} for name, pages in sorted(documents().items())]}


@app.post("/documents")
def post_document(body: dict):
    try:
        return add_document(body.get("name"), body.get("content_base64"))
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
