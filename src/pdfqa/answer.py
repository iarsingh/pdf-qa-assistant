import base64
import binascii
import hashlib
import math
import re
import zlib
from pathlib import Path

DIM = 64
STOP = {"the", "a", "an", "is", "of", "and", "to", "in", "what", "why", "does", "when", "who", "how", "can", "do"}
ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,60}\.pdf$")
MAX_BYTES = 2_000_000
MAX_DOCUMENTS = 20
STREAM = re.compile(rb"<<((?:(?!<<|>>).)*)>>\s*stream\r?\n(.*?)\r?\nendstream", re.S)
TEXT_OP = re.compile(rb"\(((?:\\.|[^\\)])*)\)\s*(?:Tj|'|\")|\[((?:[^\]\\]|\\.)*)\]\s*TJ", re.S)
LITERAL = re.compile(rb"\(((?:\\.|[^\\)])*)\)", re.S)
ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}

UPLOADED = {}


class DocumentError(ValueError):
    pass


def unescape(raw):
    def replace(match):
        token = match.group(1)
        if token[:1].isdigit():
            return bytes([int(token, 8) & 0xFF])
        return ESCAPES.get(token, token)

    return re.sub(rb"\\([0-7]{1,3}|.)", replace, raw, flags=re.S).decode("latin-1")


def stream_text(body):
    parts = []
    for match in TEXT_OP.finditer(body):
        if match.group(1) is not None:
            parts.append(unescape(match.group(1)))
        else:
            parts.extend(unescape(item) for item in LITERAL.findall(match.group(2)))
    return " ".join(part.strip() for part in parts if part.strip())


def extract_pages(data):
    pages = []
    for header, body in STREAM.findall(data):
        if b"/FlateDecode" in header:
            try:
                body = zlib.decompress(body)
            except zlib.error:
                continue
        text = stream_text(body)
        if text:
            pages.append(text)
    if not pages:
        legacy = " ".join(unescape(item) for item in LITERAL.findall(data)).strip()
        if legacy:
            pages.append(legacy)
    return [(number, text) for number, text in enumerate(pages, start=1)]


def extract_pdf_text(data):
    return " ".join(text for _, text in extract_pages(data))


def load_corpus():
    return {path.name: extract_pages(path.read_bytes()) for path in sorted((ROOT / "corpus").glob("*.pdf"))}


def documents():
    return {**load_corpus(), **UPLOADED}


def add_document(name, content_base64):
    if not isinstance(name, str) or not NAME.match(name):
        raise DocumentError("name must look like runbook.pdf: lowercase letters, digits, dash, underscore")
    if name in load_corpus():
        raise DocumentError("name is taken by a corpus document")
    if name not in UPLOADED and len(UPLOADED) >= MAX_DOCUMENTS:
        raise DocumentError(f"at most {MAX_DOCUMENTS} uploaded documents")
    try:
        data = base64.b64decode(content_base64 or "", validate=True)
    except (binascii.Error, TypeError) as exc:
        raise DocumentError("content_base64 is not valid base64") from exc
    if len(data) > MAX_BYTES:
        raise DocumentError(f"PDF is larger than {MAX_BYTES} bytes")
    if not data.startswith(b"%PDF-"):
        raise DocumentError("file does not start with %PDF-")
    pages = extract_pages(data)
    if not pages:
        raise DocumentError("no extractable text; a scanned PDF needs OCR first")
    UPLOADED[name] = pages
    return {"name": name, "pages": len(pages)}


def embed(text):
    vector = [0.0] * DIM
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        vector[digest[0] % DIM] += 1.0 if digest[1] % 2 == 0 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP


def passages():
    for name, pages in documents().items():
        for number, text in pages:
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                if sentence.strip():
                    yield {"source": name, "page": number, "text": sentence.strip()}


def answer(question, top_k=3):
    if not isinstance(question, str) or not question.strip():
        raise DocumentError("question is empty")
    if not isinstance(top_k, int) or not 1 <= top_k <= 10:
        raise DocumentError("top_k must be from 1 to 10")
    query_words = words(question)
    query = embed(question)
    hits = []
    for passage in passages():
        overlap = len(query_words & words(passage["text"]))
        score = sum(a * b for a, b in zip(query, embed(passage["text"])))
        hits.append({**passage, "overlap": overlap, "score": round(score, 4)})
    hits.sort(key=lambda hit: (hit["overlap"], hit["score"]), reverse=True)
    top = hits[:top_k]
    if not top or top[0]["overlap"] < 2:
        return {"answered": False, "answer": "No PDF passage is close enough.", "citation": None, "passages": top}
    best = top[0]
    return {"answered": True, "answer": best["text"], "citation": f"{best['source']} p.{best['page']}", "passages": top}
