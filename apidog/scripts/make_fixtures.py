"""
Generate small valid fixture files for Apidog multipart upload tests.

The mock-api only validates extension (.pdf/.png/.jpg/.jpeg) and 5 MB size cap,
so even tiny placeholder files work fine.

Usage:
    python apidog/scripts/make_fixtures.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)


def make_minimal_pdf(path: Path) -> None:
    """Hand-rolled minimal PDF that says 'Sample receipt - 42.50 EUR'."""
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 58>>stream\n"
        b"BT /F1 14 Tf 20 60 Td (Sample receipt - 42.50 EUR) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    )
    # Build xref with correct offsets
    offsets = [0]
    pos = 0
    for line in body.split(b"endobj\n")[:-1]:
        offsets.append(pos)
        pos += len(line) + len(b"endobj\n")
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
    trailer += f"{len(body)}\n".encode()
    trailer += b"%%EOF\n"
    path.write_bytes(body + xref + trailer)


def make_tiny_png(path: Path) -> None:
    """A valid 1x1 transparent PNG (smallest possible valid PNG, ~70 bytes)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)  # 1x1 RGBA
    raw = b"\x00\x00\x00\x00\x00"  # 1 filter byte + 4 RGBA bytes
    idat = zlib.compress(raw, 9)
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    pdf = FIXTURES / "sample_receipt.pdf"
    png = FIXTURES / "sample_signature.png"
    make_minimal_pdf(pdf)
    make_tiny_png(png)
    print(f"Wrote {pdf} ({pdf.stat().st_size} bytes)")
    print(f"Wrote {png} ({png.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
