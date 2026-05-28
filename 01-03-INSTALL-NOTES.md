# Wave 2 Installation Notes

**Date:** 2026-05-28
**Platform:** Apple Silicon (arm64) macOS 25.4.0

## Problem: Project .venv is x86_64 (Rosetta)

The project's `.venv` was created with x86_64 Python 3.13.2 (Rosetta emulation).
PyTorch does NOT publish arm64 macOS wheels to the default PyPI index under x86_64
platform tags — only arm64 wheels exist for macOS. As a result, `torch` (and everything
that depends on it: `sentence-transformers`, `FlagEmbedding`) cannot be installed
into the project `.venv` via the standard `pip install` path.

**Root cause:** `.venv` was created with an x86_64 Python, likely because the shell
session was running under Rosetta when `python3 -m venv .venv` was run.

**Workaround applied:** All Wave 2 heavy deps installed into conda `base` environment,
which uses arm64 Python 3.13.5. The conda env is the execution environment for Wave 2+.

```bash
# Conda base (arm64) — active Python for Wave 2
/opt/anaconda3/bin/python --version  # Python 3.13.5

# Install commands used
/opt/anaconda3/bin/pip install torch                       # 2.12.0
/opt/anaconda3/bin/pip install sentence-transformers       # 5.5.1
/opt/anaconda3/bin/pip install qdrant-client rapidfuzz     # 1.18.0 / 3.14.5
/opt/anaconda3/bin/pip install pymupdf                     # 1.26.6
/opt/anaconda3/bin/pip install docling                     # 2.95.0
/opt/anaconda3/bin/pip install FlagEmbedding               # 1.4.0
/opt/anaconda3/bin/pip install pytest pytest-timeout       # 9.3.2 / 2.4.0
```

## Package Install Status

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| torch | 2.12.0 | INSTALLED (conda) | arm64 macOS only; not in project .venv |
| sentence-transformers | 5.5.1 | INSTALLED (conda) | bge-m3 wrapper |
| qdrant-client | 1.18.0 | INSTALLED (conda) | Qdrant Cloud + in-memory mode |
| rapidfuzz | 3.14.5 | INSTALLED (conda) | Fuzzy cite-check |
| pymupdf | 1.26.6 | INSTALLED (conda) | Fast PDF page access |
| docling | 2.95.0 | INSTALLED (conda) | DRHP parse engine |
| FlagEmbedding | 1.4.0 | INSTALLED (conda) | bge-reranker-v2-m3 |
| tiktoken | 0.12.0 | INSTALLED (conda) | Token counting |
| typer | 0.20.0 | INSTALLED (conda) | CLI framework |
| rich | 13.9.4 | INSTALLED (conda) | Progress bars |

## Test Execution Instructions for Wave 2+

Run tests using the conda Python:
```bash
/opt/anaconda3/bin/python -m pytest tests/ -x -q --timeout=60
```

Or activate conda base first:
```bash
conda activate base
pytest tests/ -x -q --timeout=60
```

## Fix for Future Sessions

To create a proper arm64 venv, recreate it with the conda Python:
```bash
rm -rf .venv
/opt/anaconda3/bin/python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pip install torch sentence-transformers qdrant-client docling FlagEmbedding pymupdf rapidfuzz tiktoken
```

## FlagEmbedding Status

FlagEmbedding 1.4.0 installed successfully. The `FlagReranker` class is available via
`from FlagEmbedding import FlagReranker`. No compilation errors on arm64.

## bge-m3 Model Weights

bge-m3 weights (~1.1 GB) will be downloaded to `~/.cache/huggingface/hub/` on first
`get_embedder()` call. The `@functools.lru_cache` singleton ensures download happens
only once per process.

## Deferred / Not Installed

| Package | Status | Reason |
|---------|--------|--------|
| llama-index | DEFERRED | Not needed for Wave 2; Wave 3 |
| langfuse | DEFERRED | Not needed for Wave 2; Wave 5 |
| streamlit | DEFERRED | Not needed for Wave 2; Wave 4 |
| reportlab | NOT NEEDED | Using pymupdf for synthetic PDF fixture |
