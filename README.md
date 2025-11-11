# Australian Government AI Transparency Statements

This repository tracks AI Transparency Statements from Australian Government
departments and agencies.

## Background

Under the
[Policy for the responsible use of AI in government](https://www.digital.gov.au/policy/ai/policy),
all Australian Government departments and agencies are required to publish AI
Transparency Statements on their websites. These statements must be updated at
least annually.

This project automatically scrapes these statements and stores them as markdown
files with YAML frontmatter, allowing changes to be tracked over time through
git.

## Usage

Run the scraper:

```bash
uv run scrape_ai_statements.py
```

The script will fetch all configured AI Transparency Statements and save them to
the `statements/` directory.

## Cronjob setup

To run this automatically, add to your crontab:

```bash
# Run daily at 2am
0 2 * * * cd /path/to/ausgov-ai-transparency-statements && uv run scrape_ai_statements.py && git add statements/ && git commit -m "Update AI transparency statements $(date +\%Y-\%m-\%d)" && git push
```

## Output format

Each statement is saved as a markdown file with YAML frontmatter containing:

- `department`: Department/agency name
- `slug`: Short identifier used for filename
- `source_url`: Original URL of the statement
- `final_url`: Final URL after redirects
- `fetched_at`: ISO 8601 timestamp of fetch
- `title`: Page title
- `last_modified`: Last modified date (if available in page metadata)
- `status_code`: HTTP status code
- `error`: Error message (if fetch failed)

## Adding new departments

To add a new department, edit `scrape_ai_statements.py` and add an entry to the
`DEPARTMENTS` list:

```python
Department(
    name="Department Name",
    slug="shortname",
    url="https://example.gov.au/ai-transparency-statement"
)
```

## Requirements

- `uv` (for python wrangling)

That's it---dependencies are automatically installed by uv from the script's
inline metadata.

## Author

(c) Ben Swift

A _Cybernetic Studio_ project.

## License

MIT
