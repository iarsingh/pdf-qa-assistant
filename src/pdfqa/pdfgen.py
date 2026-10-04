import sys
import zlib
from pathlib import Path


def escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


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
            extra = " /Filter /FlateDecode"
        objects[content_id] = f"<< /Length {len(data)}{extra} >>\nstream\n".encode() + data + b"\nendstream"

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n".encode() + objects[object_id] + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for object_id in sorted(objects):
        out += f"{offsets[object_id]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


HANDBOOK = [
    [
        "Release handbook.",
        "Every production deploy needs an approved change ticket.",
        "The platform refuses latest image tags in production.",
    ],
    [
        "Rollback.",
        "The on-call engineer may roll back without approval when the error rate doubles.",
        "A rollback is announced in the incident channel within five minutes.",
    ],
    [
        "Error budget.",
        "The monthly error budget is 43 minutes of downtime.",
        "When the budget is spent, feature releases pause until the next month.",
    ],
]


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("corpus/handbook.pdf")
    target.write_bytes(build(HANDBOOK))
    print(f"wrote {target}")
