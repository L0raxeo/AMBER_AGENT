# AMBER Agent

An intelligent Python CLI assistant that helps molecular dynamics researchers generate accurate AMBER/CPPTRAJ commands through natural language queries. Built for local execution with LLM-powered command generation.

## What This Agent Does

AMBER Agent bridges the gap between complex molecular dynamics software documentation and user intent. Instead of manually searching through 1000+ page manuals, you can ask in plain English and get precise, contextual commands.

**Example Workflow:**
```
You: "calculate distance between atoms"
Agent: Finds 'distance' command → Reads relevant manual pages → Generates:

distance dist1 :1@CA :10@CA out distances.dat
```

The agent doesn't just guess - it reads the actual AMBER manual pages and provides commands based on official documentation.

## Agent Capabilities

### 🎯 **Smart Command Matching**
- Indexes 1200+ AMBER commands from official documentation
- Uses fuzzy matching to interpret natural language queries
- Handles typos, synonyms, and partial command names

### 📖 **Context-Aware Documentation Reading**
- Automatically extracts relevant manual sections (not entire 1000+ page manual)
- Provides LLM with precise context for each command
- Ensures responses are based on official AMBER documentation

### 🧠 **Intelligent Command Generation**
- Generates syntactically correct AMBER/CPPTRAJ commands
- Suggests reasonable defaults for unspecified parameters
- Explains parameter choices when needed
- Can provide multiple approaches for complex tasks

### ⚡ **Performance Optimized**
- Local processing minimizes API calls (only LLM inference is remote)
- Intelligent caching prevents redundant API requests
- Optional text preprocessing for faster lookups
- Token-efficient prompting saves costs

### 🔧 **Developer Friendly**
- Simple CLI interface with comprehensive options
- Virtual environment isolation
- Easy installation and packaging
- Configurable confidence thresholds

## Quick Start

### 1. Prerequisites

- Python 3.10+
- An OpenAI API key (or other compatible LLM API)

### 2. Installation

```bash
# Clone or create the project directory
cd amber-agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or: .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Prepare PDFs

You need two PDF files:
- `AMBER_Manual.pdf` - The full AMBER manual
- `AMBER_Index.pdf` - Just the index pages (extract from the full manual)

To extract the index:
1. Open `AMBER_Manual.pdf` in a PDF viewer
2. Find the index section (usually last ~13 pages)
3. "Print to PDF" just those pages and save as `AMBER_Index.pdf`

### 4. Build the Index

```bash
python build_index.py
```

This will:
- Parse the index PDF to create `docs/index.json`
- Slice the manual into mini-PDFs for each command in `docs/`

### 5. Use the CLI

```bash
# Basic usage
python amber_agent.py make "RMSF backbone by residue frames 1-102 in cpptraj"

# With options
python amber_agent.py make "calculate distance between atoms" --program cpptraj --min-score 60
```

## Optional Enhancements

### Text Sidecars (Recommended)

Extract text from PDFs once for faster processing:

```bash
python extract_text_sidecars.py
```

This creates `.txt` files in `docs/` that the CLI will prefer over re-reading PDFs.

### Install as System Command

```bash
# Local development install
pip install -e .

# Now you can use anywhere:
amber-agent make "rmsd protein heavy atoms 1-100"
```

Or with pipx:
```bash
pipx install .
amber-agent make "your query here"
```

## Usage Examples

```bash
# RMSF calculation
python amber_agent.py make "RMSF for backbone by residue from frame 1 to 102"

# Distance calculation
python amber_agent.py make "measure distance between residue 10 and 20"

# With specific program
python amber_agent.py make "cluster analysis" --program cpptraj

# Clear cache
python amber_agent.py clear-cache
```

## CLI Options

- `--program`: AMBER tool to use (default: cpptraj)
- `--model`: LLM model (default: from env or gpt-4o-mini)
- `--temperature`: LLM temperature (default: 0.2)
- `--min-score`: Fuzzy match threshold 0-100 (default: 70)
- `--max-chars`: Limit manual text to control tokens (default: 12000)
- `--use-cache/--no-use-cache`: Enable/disable caching (default: enabled)

## Project Structure

```
amber-agent/
├── AMBER_Manual.pdf          # Full manual (you provide)
├── AMBER_Index.pdf           # Index pages (you extract)
├── docs/                     # Generated files
│   ├── index.json           # Command → page mappings
│   ├── *.pdf                # Mini-PDFs per command
│   └── *.txt                # Text sidecars (optional)
├── .cache/                   # LLM response cache
├── .env                      # Your API key
├── requirements.txt          # Dependencies
├── build_index.py           # PDF parser
├── amber_agent.py           # Main CLI
├── extract_text_sidecars.py # Text extraction utility
└── pyproject.toml           # Package config
```

## How It Works

1. **Index Parsing**: Extracts command names and page ranges from the index PDF
2. **Fuzzy Matching**: Matches user queries to command names using RapidFuzz
3. **Context Loading**: Reads only the relevant manual pages for the matched command
4. **LLM Query**: Sends focused context to LLM with specific prompt
5. **Caching**: Saves responses to avoid repeat API calls

## Troubleshooting

- **"No confident command match"**: Try different keywords or lower `--min-score`
- **"Missing AMBER_Index.pdf"**: Extract index pages from the full manual
- **API errors**: Check your `.env` file and API key
- **Bad page ranges**: The index extraction may need adjustment

## Maintenance

When the AMBER manual updates:
1. Replace `AMBER_Manual.pdf` and `AMBER_Index.pdf`
2. Run `python build_index.py`
3. Optionally run `python extract_text_sidecars.py`
4. Clear cache with `python amber_agent.py clear-cache`