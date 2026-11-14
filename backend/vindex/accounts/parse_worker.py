"""Resource-limited document-to-text child. No application secrets are inherited."""

import io
import json
import resource
import sys
import zipfile

MAX_TEXT = 100_000


def extract(data: bytes, kind: str) -> str:
    if kind == "txt":
        text = data.decode("utf-8-sig")
        if "\x00" in text or data.startswith((b"%PDF-", b"PK\x03\x04")):
            raise ValueError("binary_text")
    elif kind == "pdf":
        from pypdf import PdfReader
        from pypdf.generic import DictionaryObject

        if not data.startswith(b"%PDF-"):
            raise ValueError("invalid_pdf")
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted or len(reader.pages) > 20:
            raise ValueError("encrypted_or_too_many_pages")
        root = reader.trailer["/Root"].get_object()
        if not isinstance(root, DictionaryObject):
            raise ValueError("invalid_pdf_root")
        names = root.get("/Names", {})
        if hasattr(names, "get_object"):
            names = names.get_object()
        if not isinstance(names, dict):
            raise ValueError("invalid_pdf_names")
        opening = root.get("/OpenAction")
        if opening is not None and hasattr(opening, "get_object"):
            opening = opening.get_object()
        if isinstance(opening, dict) and opening.get("/S") != "/GoTo":
            raise ValueError("active_document")
        if any(k in root for k in ("/AA", "/AcroForm")) or any(
            k in names for k in ("/JavaScript", "/EmbeddedFiles")
        ):
            raise ValueError("active_document")
        text_parts = []
        for page in reader.pages:
            if "/AA" in page:
                raise ValueError("active_document")
            text_parts.append(page.extract_text() or "")
            if sum(len(part) for part in text_parts) > MAX_TEXT:
                raise ValueError("too_much_text")
        text = "\n".join(text_parts)
    elif kind == "docx":
        from defusedxml import ElementTree

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(e.file_size for e in entries) > 20 * 1024 * 1024:
                raise ValueError("archive_budget")
            if any(e.flag_bits & 1 or e.filename.lower().endswith(".bin") for e in entries):
                raise ValueError("encrypted_or_active_archive")
            if (
                len({e.filename for e in entries}) != len(entries)
                or "[Content_Types].xml" not in archive.namelist()
            ):
                raise ValueError("invalid_docx")
            xml_root = ElementTree.fromstring(archive.read("word/document.xml"), forbid_dtd=True)
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

            def paragraph_text(paragraph):
                return "".join(
                    node.text or "" if node.tag == ns + "t" else "\n"
                    for node in paragraph.iter()
                    if node.tag in {ns + "t", ns + "br"}
                )

            body = xml_root.find(ns + "body")
            if body is None:
                raise ValueError("invalid_docx_body")
            lines = []
            for block in body:
                if block.tag == ns + "tbl":
                    for row in block.findall(ns + "tr"):
                        cells = [
                            " ".join(paragraph_text(p).strip() for p in cell.iter(ns + "p"))
                            for cell in row.findall(ns + "tc")
                        ]
                        lines.append(" | ".join(cell for cell in cells if cell))
                else:
                    lines.extend(paragraph_text(p) for p in block.iter(ns + "p"))
            text = "\n".join(lines)
    else:
        raise ValueError("unsupported_type")
    if len(text) > MAX_TEXT:
        raise ValueError("too_much_text")
    if not text.strip():
        raise ValueError("no_selectable_text")
    return text


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform == "linux":
        budget = 512 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (budget, budget))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        data = sys.stdin.buffer.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("too_large")
        text = extract(data, sys.argv[1])
        print(json.dumps({"text": text}))
    except Exception as error:
        # Parser diagnostics must never reveal resume contents or local paths.
        print(
            json.dumps(
                {"error": str(error) if str(error) == "no_selectable_text" else "unreadable"}
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
