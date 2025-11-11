# Agent guidelines

This is a Python web scraping project using uv for dependency management.

## Key context

- Uses `uv` for package management (inline script metadata in
  `scrape_ai_statements.py`)
- Project has `mise.toml`---prefix commands with `mise exec --`
- Scrapes Australian Government AI transparency statements from department
  websites
- Converts HTML/PDF to markdown with YAML frontmatter
- Tracks changes via git commits (designed for cron jobs)
- Dependencies: httpx, beautifulsoup4, html2text, lxml, PyPDF2, pyyaml

## Working on this project

- Run scraper: `mise exec -- uv run scrape_ai_statements.py`
- Run tests: `mise exec -- uv run pytest`
- Add departments by editing the `DEPARTMENTS` list in `scrape_ai_statements.py`
- Output goes to `statements/` directory

## Code patterns

- Uses `NamedTuple` for data classes (Department)
- Type hints throughout
- Returns dicts with explicit `str | int | None` types
- Handles both HTML and PDF sources
- Follows structured logging with stdlib `logging`
