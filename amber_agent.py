import os, json, pathlib, typer, hashlib
from rapidfuzz import process, fuzz
from dotenv import load_dotenv

# LLM (OpenAI)
from openai import OpenAI

app = typer.Typer(help="AMBER command/script builder (local CLI + LLM API)")
ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
CACHE = ROOT / ".cache"
CACHE.mkdir(exist_ok=True)

def load_index():
    idx_path = DOCS / "index.json"
    if not idx_path.exists():
        typer.echo("ERROR: docs/index.json not found. Run: python build_index.py")
        raise typer.Exit(1)
    return json.loads(idx_path.read_text())

def best_match(query: str, choices):
    m = process.extractOne(query.lower(), choices, scorer=fuzz.WRatio)
    return (m[0], m[1]) if m else (None, 0)

def _format_pages(meta):
    """Helper function to format page numbers for display"""
    if "pages" in meta:
        pages = sorted(meta["pages"])
        if len(pages) == 1:
            return str(pages[0])
        elif len(pages) == 2 and pages[1] == pages[0] + 1:
            return f"{pages[0]}-{pages[1]}"
        else:
            return ", ".join(map(str, pages))
    else:
        # Fallback for old format
        if meta["start"] == meta["end"]:
            return str(meta["start"])
        else:
            return f"{meta['start']}-{meta['end']}"

def read_pages_text_from_manual(cmd, meta, manual_path="AMBER_Manual.pdf"):
    # Check if text sidecar exists first (try both original and sanitized names)
    txt_path = DOCS / f"{cmd}.txt"
    if not txt_path.exists():
        # Try sanitized filename
        safe_cmd = cmd.replace("/", "_").replace("\\", "_").replace(":", "_").replace("+", "plus")
        safe_cmd = "".join(c for c in safe_cmd if c.isalnum() or c in "._-")
        txt_path = DOCS / f"{safe_cmd}.txt"
    
    if txt_path.exists():
        return txt_path.read_text()
    
    # Pull the actual pages from the big manual to avoid stale minis
    import fitz
    
    # Handle both old format (start/end) and new format (pages)
    if "pages" in meta:
        # Apply +1 offset to each page for correct content
        actual_pages = []
        for page in meta["pages"]:
            actual_pages.extend([page + 1, page + 2])  # +1 offset, then include next page
        # Remove duplicates and sort, then convert to zero-based
        page_numbers = [p - 1 for p in sorted(set(actual_pages))]
    else:
        # Fallback for old format
        start, end = meta["start"] - 1, meta["end"] - 1
        page_numbers = list(range(start, end + 1))
    
    manual_file = ROOT / manual_path
    if not manual_file.exists():
        typer.echo(f"ERROR: {manual_path} not found")
        raise typer.Exit(1)
    
    with fitz.open(manual_file) as book:
        chunks = []
        for p in page_numbers:
            if 0 <= p < len(book):
                chunks.append(book[p].get_text())
    return "\n".join(chunks)

def llm_client():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        typer.echo("ERROR: OPENAI_API_KEY not set (use .env or export in shell)")
        raise typer.Exit(1)
    return OpenAI(api_key=api_key)

def cache_key(cmd, query, model):
    h = hashlib.sha1(f"{cmd}|{query}|{model}".encode()).hexdigest()
    return CACHE / f"{h}.md"

SYSTEM = """You are an AMBER/CPPTRAJ assistant.
Only use the provided manual excerpts to craft exact commands or minimal scripts.
If there are multiple valid approaches, show the *most canonical* one, then one alternative.
Return the final command(s) in fenced code blocks with no commentary inside the blocks.
If parameters are unspecified by the user, pick sane defaults and call them out.
"""

@app.command()
def make(
    query: str = typer.Argument(..., help="What the user wants (e.g., 'RMSF backbone by residue frames 1-102 in cpptraj')"),
    program: str = typer.Option("cpptraj", help="AMBER tool, e.g., cpptraj"),
    model: str = typer.Option(os.getenv("OPENAI_MODEL", "gpt-4o-mini")),
    temperature: float = typer.Option(0.2),
    min_score: int = typer.Option(70, help="Fuzzy match confidence threshold (0-100)"),
    max_chars: int = typer.Option(12000, help="Cap manual text to control tokens"),
    use_cache: bool = typer.Option(True, help="Use cached responses when available"),
):
    """
    Find the command in the manual index, read only those pages, and ask the LLM to build the command/script.
    """
    index = load_index()
    choices = list(index.keys())
    cmd, score = best_match(query, choices)
    if not cmd or score < min_score:
        typer.echo(f"No confident command match (best='{cmd}' score={score}). Try a different keyword.")
        raise typer.Exit(2)

    # Check cache first
    if use_cache:
        out_path = cache_key(cmd, query, model)
        if out_path.exists():
            print(out_path.read_text())
            return

    pages_meta = index[cmd]
    text = read_pages_text_from_manual(cmd, pages_meta)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[...truncated for token limits ...]"

    user_prompt = (
        f"Program: {program}\n"
        f"User request: {query}\n"
        f"AMBER manual pages for '{cmd}' (pp. {_format_pages(pages_meta)}):\n"
        f"{text}"
    )

    client = llm_client()
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    )
    
    result = resp.choices[0].message.content
    
    # Cache the result
    if use_cache:
        out_path = cache_key(cmd, query, model)
        out_path.write_text(result)
    
    print(result)

@app.command()
def clear_cache():
    """Clear all cached responses."""
    import shutil
    if CACHE.exists():
        shutil.rmtree(CACHE)
        CACHE.mkdir()
        typer.echo("Cache cleared")
    else:
        typer.echo("Cache directory doesn't exist")

if __name__ == "__main__":
    app()