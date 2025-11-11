"""Australian Government AI Transparency Statement Scraper."""

from .scraper import (
    Department,
    clean_html_to_markdown,
    extract_main_content,
    fetch_statement,
    load_departments,
    save_statement,
)

__all__ = [
    "Department",
    "clean_html_to_markdown",
    "extract_main_content",
    "fetch_statement",
    "load_departments",
    "save_statement",
]
