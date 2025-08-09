import json, re, sys, pathlib
import fitz  # PyMuPDF

INDEX_PDF = pathlib.Path("/Users/cheng/Documents/gogovi/amber-agent/AMBER_Index.pdf")
MANUAL_PDF = pathlib.Path("/Users/cheng/Documents/gogovi/amber-agent/AMBER_Manual.pdf")
DOCS_DIR   = pathlib.Path("docs")
DOCS_DIR.mkdir(exist_ok=True)

# Flexible index line patterns for AMBER format (comma-separated pages)
PATTERNS = [
    # AMBER format: "command, page1, page2, page3"
    re.compile(r'^\s*([A-Za-z0-9_\\:+\-/\.]+),\s*(\d+)(?:,\s*\d+)*\s*$'),
    # Traditional dot leaders format
    re.compile(r'^\s*([A-Za-z0-9_:+\-/\.]+)\s+\.{3,}\s+(\d+)(?:\s*[-–]\s*(\d+))?\s*'),
    # Page format with "p."
    re.compile(r'^\s*([A-Za-z0-9_:+\-/\.]+)\s+[, ]*\s*p\.?\s*(\d+)(?:\s*[-–]\s*(\d+))?\s*', re.IGNORECASE),
]

def parse_index_text(txt: str):
    mapping = {}
    for raw in txt.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith(("see ", "seealso", "…", "index")):
            continue
        
        # Handle AMBER comma-separated format first
        if ',' in line:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 2:
                cmd = parts[0]
                pages = []
                for p in parts[1:]:
                    if p.isdigit():
                        pages.append(int(p))
                
                if pages and cmd:
                    key = cmd.lower()
                    # Store individual pages, not ranges
                    rng = {"pages": pages}
                    # If duplicates, combine the page lists
                    if key in mapping:
                        existing_pages = mapping[key].get("pages", [])
                        combined_pages = list(set(existing_pages + pages))  # Remove duplicates
                        mapping[key] = {"pages": combined_pages}
                    else:
                        mapping[key] = rng
                    continue
        
        # Fallback to traditional patterns
        m = None
        for pat in PATTERNS[1:]:  # Skip the comma pattern we handled above
            m = pat.match(line)
            if m:
                break
        if not m:
            continue
        cmd, start, end = m.group(1), int(m.group(2)), m.group(3)
        key = cmd.lower()
        start_page = int(start)
        end_page = int(end) if end else int(start)
        pages = list(range(start_page, end_page + 1))
        rng = {"pages": pages}
        # If duplicates, combine the page lists
        if key in mapping:
            existing_pages = mapping[key].get("pages", [])
            combined_pages = list(set(existing_pages + pages))  # Remove duplicates
            mapping[key] = {"pages": combined_pages}
        else:
            mapping[key] = rng
    return mapping

def extract_index_pdf():
    if not INDEX_PDF.exists():
        sys.exit("Missing AMBER_Index.pdf")
    doc = fitz.open(INDEX_PDF)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text

def slice_command_pdfs(index_map):
    if not MANUAL_PDF.exists():
        sys.exit("Missing AMBER_Manual.pdf")
    book = fitz.open(MANUAL_PDF)
    for cmd, rng in index_map.items():
        # Handle both old format (start/end) and new format (pages)
        if "pages" in rng:
            index_pages = rng["pages"]
        else:
            # Fallback for old format
            index_pages = list(range(rng["start"], rng["end"] + 1))
        
        # Apply +1 offset to each page and include the following page
        actual_pages = []
        for page in index_pages:
            actual_pages.extend([page + 1, page + 2])  # +1 offset, then include next page
        
        # Remove duplicates and sort
        actual_pages = sorted(set(actual_pages))
        
        # Convert to zero-based and validate
        zero_based_pages = [p - 1 for p in actual_pages if 0 <= p - 1 < len(book)]
        
        if not zero_based_pages:
            print(f"[WARN] No valid pages for {cmd}: {index_pages}")
            continue
        
        # Sanitize filename - replace problematic characters
        safe_cmd = cmd.replace("/", "_").replace("\\", "_").replace(":", "_").replace("+", "plus")
        safe_cmd = "".join(c for c in safe_cmd if c.isalnum() or c in "._-")
        
        out = fitz.open()
        for page_num in zero_based_pages:
            out.insert_pdf(book, from_page=page_num, to_page=page_num)
        out.save(DOCS_DIR / f"{safe_cmd}.pdf")
        out.close()
    book.close()

if __name__ == "__main__":
    index_text = extract_index_pdf()
    idx = parse_index_text(index_text)
    (DOCS_DIR / "index.json").write_text(json.dumps(idx, indent=2))
    print(f"[OK] Parsed {len(idx)} index entries → docs/index.json")
    slice_command_pdfs(idx)
    print(f"[OK] Wrote mini-PDFs to {DOCS_DIR}/")
