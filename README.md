# Australian Government AI Transparency Statements

This repository tracks AI Transparency Statements from Australian Government
agencies.

## Background

Under the
[Policy for the responsible use of AI in government](https://www.digital.gov.au/policy/ai/policy),
all Australian Government agencies are required to publish AI Transparency
Statements on their websites. These statements must be updated at least
annually.

This project automatically scrapes these statements and stores them as markdown
files with YAML frontmatter, allowing changes to be tracked over time through
git.

## Usage

Run the scraper:

```bash
uv run --module ausgov_ai_transparency_statements
```

Or use the installed command (after `uv sync`):

```bash
scrape-ai-statements
```

The script will fetch all configured AI Transparency Statements and save them to
the `statements/` directory.

## Cronjob setup

To run this automatically, add to your crontab:

```bash
# Run daily at 2am
0 2 * * * cd /path/to/ausgov-ai-transparency-statements && uv run --module ausgov_ai_transparency_statements && git add statements/ && git commit -m "Update AI transparency statements $(date +\%Y-\%m-\%d)" && git push
```

## Output format

Each statement is saved as a markdown file with YAML frontmatter containing:

- `agency`: Agency name
- `slug`: Short identifier used for filename
- `source_url`: Original URL of the statement
- `final_url`: Final URL after redirects
- `fetched_at`: ISO 8601 timestamp of fetch
- `title`: Page title
- `last_modified`: Last modified date (if available in page metadata)
- `status_code`: HTTP status code
- `error`: Error message (if fetch failed)

## Adding new agencies

To add a new agency, edit `agencies.toml` and add a new entry:

```toml
[[agencies]]
name = "Agency Name"
slug = "shortname"
url = "https://example.gov.au/ai-transparency-statement"
```

## Requirements

- `uv` (for Python package management)

That's it---dependencies are automatically installed by uv from
`pyproject.toml`.

## Author

(c) Ben Swift

A _Cybernetic Studio_ project.

## License

MIT
