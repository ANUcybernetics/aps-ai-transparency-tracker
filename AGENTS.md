# Agent guidelines

This is a Python web scraping project using uv for dependency management.

## Key context

- Uses `uv` for package management with proper package structure
- Project has `mise.toml`---prefix commands with `mise exec --`
- Scrapes Australian Government AI transparency statements from agency websites
- Converts HTML/PDF to markdown with YAML frontmatter
- Tracks changes via git commits (designed for cron jobs)
- Dependencies defined in `pyproject.toml`: httpx, beautifulsoup4, html2text,
  lxml, pypdf, pyyaml

## Working on this project

- Run scraper: `mise exec -- uv run --module ausgov_ai_transparency_statements`
- Run tests: `mise exec -- uv run pytest`
- Add agencies by editing `agencies.toml`
- Output goes to `statements/` directory
- Package structure:
  - `src/ausgov_ai_transparency_statements/` contains the package
  - `scraper.py` has core functionality
  - `__main__.py` provides CLI entry point

## Code patterns

- Uses `NamedTuple` for data classes (Agency)
- Type hints throughout
- Returns dicts with explicit `str | int | None` types
- Handles both HTML and PDF sources
- Follows structured logging with stdlib `logging`
