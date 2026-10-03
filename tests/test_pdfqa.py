from fastapi.testclient import TestClient
from pdfqa.main import app

def test_answers_from_the_pdf_and_refuses_an_unrelated_question():
    client = TestClient(app)
    hit = client.post("/ask", json={"question": "What does the platform refuse in production?"}).json()
    assert hit["answered"] is True
    assert "production" in hit["answer"]
    miss = client.post("/ask", json={"question": "What is the cafeteria menu?"}).json()
    assert miss["answered"] is False
