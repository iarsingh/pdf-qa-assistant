from fastapi import FastAPI
from pdfqa.answer import answer

app = FastAPI()

@app.post("/ask")
def post_ask(body: dict):
    return answer(body["question"])
