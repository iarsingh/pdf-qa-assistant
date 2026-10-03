import hashlib
import math
import re
from pathlib import Path

DIM = 64
STOP = {"the", "a", "an", "is", "of", "and", "to", "in", "what", "why", "does"}
ROOT = Path(__file__).resolve().parents[2]

def extract_pdf_text(data):
    parts = re.findall(r"\(([^)]*)\)", data.decode("latin1", errors="ignore"))
    return " ".join(parts)

def load_corpus():
    text = extract_pdf_text((ROOT / "corpus" / "policy.pdf").read_bytes())
    return [("corpus/policy.pdf", text)]

def embed(text):
    vector = [0.0] * DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        vector[digest[0] % DIM] += 1.0 if digest[1] % 2 == 0 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]

def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP

def answer(question):
    corpus = load_corpus()
    query = embed(question)
    hits = []
    for source, text in corpus:
        score = sum(a * b for a, b in zip(query, embed(text)))
        hits.append({"source": source, "text": text, "score": round(score, 4)})
    best = hits[0]
    overlap = words(question) & words(best["text"])
    if len(overlap) < 2:
        return {"answered": False, "answer": "No PDF passage is close enough.", "passages": hits}
    return {"answered": True, "answer": best["text"], "passages": hits}
