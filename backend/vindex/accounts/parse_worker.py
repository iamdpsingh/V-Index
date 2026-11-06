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
        reader = PdfReader(io.BytesIO(data), strict=True)
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
        if any(k in root for k in ("/OpenAction", "/AA", "/AcroForm")) or any(
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
            text = "\n".join(
                " ".join(node.text or "" for node in paragraph.iter(ns + "t"))
                for paragraph in xml_root.iter(ns + "p")
            )
    else:
        raise ValueError("unsupported_type")
    if len(text) > MAX_TEXT or len(text.strip()) < 20:
        raise ValueError("unreadable_or_too_much_text")
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
    except Exception:
        # Parser diagnostics must never reveal resume contents or local paths.
        print(
            json.dumps(
                {
                    "error": "Document is unreadable, unsupported, encrypted or exceeds parsing limits"
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
