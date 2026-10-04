import base64

import pytest
from fastapi.testclient import TestClient

from pdfqa.answer import UPLOADED, extract_pages
from pdfqa.main import app
from pdfqa.pdfgen import build

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_uploads():
    UPLOADED.clear()
    yield
    UPLOADED.clear()


def upload(name, data):
    return client.post("/documents", json={"name": name, "content_base64": base64.b64encode(data).decode()})


def test_answers_from_the_pdf_and_refuses_an_unrelated_question():
    hit = client.post("/ask", json={"question": "What does the platform refuse in production?"}).json()
    assert hit["answered"] is True
    assert "production" in hit["answer"]
    assert hit["citation"].endswith("p.1")
    miss = client.post("/ask", json={"question": "What is the cafeteria menu?"}).json()
    assert miss["answered"] is False
    assert miss["citation"] is None


def test_extracts_each_page_and_unescapes_parentheses():
    pages = extract_pages(build([["Line one (draft)."], ["Path C:\\tmp is local."]]))
    assert pages == [(1, "Line one (draft)."), (2, "Path C:\\tmp is local.")]


def test_extracts_flate_compressed_streams():
    pages = extract_pages(build([["Compressed page text."]], compress=True))
    assert pages == [(1, "Compressed page text.")]


def test_uploaded_multi_page_pdf_is_cited_by_page():
    data = build([["Intro page."], ["Database failover takes ninety seconds on average."]])
    assert upload("runbook.pdf", data).json() == {"name": "runbook.pdf", "pages": 2}
    hit = client.post("/ask", json={"question": "How long does database failover take?"}).json()
    assert hit["answered"] is True
    assert hit["citation"] == "runbook.pdf p.2"


def test_bad_uploads_are_refused():
    assert upload("notes.pdf", b"hello, not a pdf").status_code == 422
    assert upload("Bad Name.pdf", build([["x y z."]])).status_code == 422
    bad_base64 = client.post("/documents", json={"name": "a.pdf", "content_base64": "%%%"})
    assert bad_base64.status_code == 422


def test_pdf_without_text_is_refused():
    response = upload("scan.pdf", build([[]]))
    assert response.status_code == 422
    assert "OCR" in response.json()["detail"]


def test_documents_lists_corpus_and_uploads():
    upload("runbook.pdf", build([["One."], ["Two."], ["Three."]]))
    names = {doc["name"]: doc["pages"] for doc in client.get("/documents").json()["documents"]}
    assert names["runbook.pdf"] == 3
    assert "policy.pdf" in names


def test_question_and_top_k_are_validated():
    assert client.post("/ask", json={"question": "  "}).status_code == 422
    assert client.post("/ask", json={"question": "rollback approval", "top_k": 0}).status_code == 422
    assert len(client.post("/ask", json={"question": "platform production", "top_k": 1}).json()["passages"]) == 1
