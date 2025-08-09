import json, pathlib, fitz

DOCS = pathlib.Path("docs")
MANUAL = pathlib.Path("AMBER_Manual.pdf")

if not MANUAL.exists():
    print("ERROR: AMBER_Manual.pdf not found")
    exit(1)

if not (DOCS / "index.json").exists():
    print("ERROR: docs/index.json not found. Run: python build_index.py")
    exit(1)

idx = json.loads((DOCS / "index.json").read_text())
book = fitz.open(MANUAL)

extracted = 0
for cmd, rng in idx.items():
    start, end = rng["start"] - 1, rng["end"] - 1
    if start < 0 or end >= len(book) or start > end:
        print(f"[WARN] Skipping {cmd}: bad range {rng['start']}-{rng['end']}")
        continue
    text = "\n".join(book[p].get_text() for p in range(start, end + 1))
    (DOCS / f"{cmd}.txt").write_text(text)
    extracted += 1

book.close()
print(f"[OK] Extracted text for {extracted} commands to docs/*.txt")