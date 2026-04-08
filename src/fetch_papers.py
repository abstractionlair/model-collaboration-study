"""Fetch full paper content for literature review.

Reads paper-votes.md, extracts arXiv IDs, and fetches full text.
Tries sources in quality order:
1. arXiv LaTeX source (best — models read LaTeX natively)
2. arXiv HTML (structured, newer papers only)
3. LlamaParse PDF extraction (premium mode, good equation recovery)

Adapted from ai-research-ontology/extraction/paper_fetcher.py.

Usage:
    python src/fetch_papers.py                    # fetch all voted papers
    python src/fetch_papers.py --min-votes 2      # only 2+ vote papers
    python src/fetch_papers.py --paper 2407.04622  # fetch one paper
    python src/fetch_papers.py --no-cache          # re-fetch everything
"""

from __future__ import annotations

import gzip
import io
import logging
import os
import re
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
VOTES_FILE = PROJECT_ROOT / "docs" / "literature" / "paper-votes.md"
CACHE_DIR = PROJECT_ROOT / "data" / "papers"

_HEADERS = {"User-Agent": "model-collaboration-study/1.0 (academic research project)"}

# Rate limiting for arXiv (be polite)
_LAST_REQUEST_TIME = 0.0
_MIN_REQUEST_INTERVAL = 3.0  # seconds between arXiv requests


def _rate_limit():
    """Ensure we don't hit arXiv too fast."""
    global _LAST_REQUEST_TIME
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _LAST_REQUEST_TIME = time.time()


def _fetch_url(url: str, timeout: int = 30) -> bytes:
    """Fetch URL content with rate limiting."""
    _rate_limit()
    req = urllib.request.Request(url, headers=_HEADERS)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read()


def _is_stub_tex(content: str) -> bool:
    """Check if a .tex file is a stub (PDF wrapper or minimal include)."""
    if r"\includepdf" in content:
        return True
    if len(content) < 3000:
        has_content = any(marker in content for marker in (
            r"\section", r"\begin{abstract}", r"\paragraph",
            r"\subsection", r"\chapter",
        ))
        if not has_content:
            return True
    return False


def _resolve_inputs(main_tex: str, all_files: dict[str, str]) -> str:
    """Resolve \\input{} and \\include{} directives by inlining content."""
    def replace_input(match):
        filename = match.group(1)
        candidates = [filename, f"{filename}.tex"]
        for candidate in candidates:
            for key in all_files:
                if key == candidate or key.endswith(f"/{candidate}"):
                    return all_files[key]
        return match.group(0)

    resolved = re.sub(
        r"(?m)^[^%]*?\\(?:input|include)\{([^}]+)\}",
        lambda m: replace_input(m) if not m.group(0).lstrip().startswith("%") else m.group(0),
        main_tex,
    )
    return resolved


def _find_main_tex(tar_bytes: bytes) -> str | None:
    """Find and read the main .tex file from an arXiv source tarball."""
    all_files: dict[str, str] = {}

    try:
        buf = io.BytesIO(tar_bytes)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    try:
                        content = tar.extractfile(member).read().decode("utf-8", errors="replace")
                        all_files[member.name] = content
                    except Exception:
                        pass
    except (tarfile.TarError, gzip.BadGzipFile):
        try:
            content = gzip.decompress(tar_bytes).decode("utf-8", errors="replace")
            if r"\documentclass" in content or r"\begin{document}" in content:
                if _is_stub_tex(content):
                    return None
                return content
        except Exception:
            pass
        return None

    tex_files = {name: content for name, content in all_files.items()
                 if name.endswith(".tex")}

    if not tex_files:
        return None

    main_candidates = {name: content for name, content in tex_files.items()
                       if r"\documentclass" in content}

    if not main_candidates:
        main_name = max(tex_files, key=lambda k: len(tex_files[k]))
        main_content = tex_files[main_name]
    elif len(main_candidates) == 1:
        main_name, main_content = next(iter(main_candidates.items()))
    else:
        main_name = None
        for preferred in ("main.tex", "paper.tex", "ms.tex", "article.tex"):
            for name in main_candidates:
                if name.endswith(preferred) or name == preferred:
                    main_name = name
                    break
            if main_name:
                break
        if not main_name:
            main_name = max(main_candidates, key=lambda k: len(main_candidates[k]))
        main_content = main_candidates[main_name]

    if _is_stub_tex(main_content):
        return None

    return _resolve_inputs(main_content, all_files)


def fetch_latex_source(arxiv_id: str) -> str | None:
    """Fetch LaTeX source from arXiv e-print endpoint."""
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    try:
        data = _fetch_url(url, timeout=30)
        tex = _find_main_tex(data)
        if tex:
            logger.info("  LaTeX source: %d chars", len(tex))
        return tex
    except Exception as e:
        logger.debug("  LaTeX fetch failed: %s", e)
        return None


def fetch_arxiv_html(arxiv_id: str) -> str | None:
    """Fetch HTML version from arXiv (newer papers only)."""
    url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        data = _fetch_url(url, timeout=30)
        html = data.decode("utf-8", errors="replace")
        if len(html) > 1000:
            logger.info("  arXiv HTML: %d chars", len(html))
            return html
        return None
    except Exception:
        return None


def fetch_pdf_llamaparse(arxiv_id: str) -> str | None:
    """Fetch PDF and parse with LlamaParse (premium mode)."""
    api_key = os.environ.get("LLAMAPARSE_API_KEY", "")
    if not api_key:
        logger.warning("  LLAMAPARSE_API_KEY not set, skipping PDF extraction")
        return None

    try:
        import tempfile
        from llama_parse import LlamaParse

        url = f"https://arxiv.org/pdf/{arxiv_id}"
        pdf_data = _fetch_url(url, timeout=60)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir="/tmp") as f:
            f.write(pdf_data)
            pdf_path = f.name

        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            premium_mode=True,
        )
        documents = parser.load_data(pdf_path)
        text = "\n\n".join(doc.text for doc in documents)

        os.unlink(pdf_path)

        if len(text) > 1000:
            logger.info("  LlamaParse PDF: %d chars", len(text))
            return text
        return None

    except Exception as e:
        logger.warning("  LlamaParse failed: %s", e)
        return None


def fetch_paper(arxiv_id: str, use_cache: bool = True) -> tuple[str, str] | None:
    """Fetch a paper by arXiv ID, trying sources in quality order.

    Returns (content, format) or None if all sources fail.
    Format is "latex", "html", or "pdf-parsed".
    """
    safe_id = arxiv_id.replace("/", "_")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if use_cache:
        for ext, fmt in [(".tex", "latex"), (".html", "html"), (".md", "pdf-parsed")]:
            cached = CACHE_DIR / f"{safe_id}{ext}"
            if cached.exists() and cached.stat().st_size > 0:
                logger.info("  cached (%s, %d chars)", fmt, cached.stat().st_size)
                return cached.read_text(), fmt

    # Try 1: LaTeX source
    tex = fetch_latex_source(arxiv_id)
    if tex:
        (CACHE_DIR / f"{safe_id}.tex").write_text(tex)
        return tex, "latex"

    # Try 2: arXiv HTML
    html = fetch_arxiv_html(arxiv_id)
    if html:
        (CACHE_DIR / f"{safe_id}.html").write_text(html)
        return html, "html"

    # Try 3: LlamaParse PDF
    parsed = fetch_pdf_llamaparse(arxiv_id)
    if parsed:
        (CACHE_DIR / f"{safe_id}.md").write_text(parsed)
        return parsed, "pdf-parsed"

    return None


def parse_votes_file(min_votes: int = 1) -> list[dict]:
    """Parse paper-votes.md and extract papers with arXiv IDs.

    Returns list of {title, arxiv_id, votes, vote_count}.
    """
    text = VOTES_FILE.read_text()
    papers = []
    current_vote_count = 0

    for line in text.splitlines():
        # Track vote count sections
        m = re.match(r"^## (\d+) Votes?", line)
        if m:
            current_vote_count = int(m.group(1))
            continue

        # Skip non-paper lines
        if not line.strip() or line.startswith("#") or line.startswith("Only") or line.startswith("One"):
            continue

        # Extract arXiv ID
        arxiv_match = re.search(r"arXiv:(\d{4}\.\d{4,5})", line)
        if not arxiv_match:
            continue

        if current_vote_count < min_votes:
            continue

        # Extract title (everything before the first parenthesis)
        title_match = re.match(r"^(.+?)\s*\(", line)
        title = title_match.group(1).strip().rstrip(":") if title_match else line.split("(")[0].strip()

        # Extract voters
        voters_match = re.search(r":\s*(.+)$", line)
        voters = voters_match.group(1).strip() if voters_match else ""

        papers.append({
            "title": title,
            "arxiv_id": arxiv_match.group(1),
            "votes": voters,
            "vote_count": current_vote_count,
        })

    return papers


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch papers from paper-votes.md")
    parser.add_argument("--min-votes", type=int, default=1,
                        help="Minimum vote count to fetch (default: 1)")
    parser.add_argument("--paper", type=str, default=None,
                        help="Fetch a single paper by arXiv ID")
    parser.add_argument("--no-cache", action="store_true",
                        help="Re-fetch even if cached")
    parser.add_argument("--dry-run", action="store_true",
                        help="List papers that would be fetched without fetching")
    args = parser.parse_args()

    if args.paper:
        logger.info("Fetching %s...", args.paper)
        result = fetch_paper(args.paper, use_cache=not args.no_cache)
        if result:
            content, fmt = result
            print(f"  {args.paper}: {fmt} ({len(content):,} chars)")
        else:
            print(f"  {args.paper}: FAILED")
            sys.exit(1)
        return

    papers = parse_votes_file(min_votes=args.min_votes)
    logger.info("Found %d papers with arXiv IDs (min_votes=%d)", len(papers), args.min_votes)

    if args.dry_run:
        for p in papers:
            print(f"  [{p['vote_count']} votes] {p['arxiv_id']}  {p['title']}")
        return

    results = {"latex": [], "html": [], "pdf-parsed": [], "failed": []}

    for i, p in enumerate(papers, 1):
        logger.info("[%d/%d] %s — %s", i, len(papers), p["arxiv_id"], p["title"])
        result = fetch_paper(p["arxiv_id"], use_cache=not args.no_cache)
        if result:
            content, fmt = result
            results[fmt].append(p["arxiv_id"])
        else:
            logger.warning("  FAILED — no source found")
            results["failed"].append(p["arxiv_id"])

    print(f"\nDone. {len(papers)} papers:")
    for fmt, ids in sorted(results.items()):
        if ids:
            print(f"  {fmt}: {len(ids)}")
    if results["failed"]:
        print(f"\nFailed papers:")
        for aid in results["failed"]:
            print(f"  {aid}")


if __name__ == "__main__":
    main()
