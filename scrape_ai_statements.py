#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx",
#     "beautifulsoup4",
#     "lxml",
#     "pyyaml",
#     "html2text",
#     "PyPDF2",
# ]
# ///
"""
Australian Government AI Transparency Statement Scraper

This script fetches AI Transparency Statements from Australian Government departments
and saves them as markdown files with YAML frontmatter. Designed to be run via cronjob
to track changes over time through git.

Usage:
    uv run scrape_ai_statements.py
"""

import logging
import re
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import html2text
import httpx
import yaml
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Department(NamedTuple):
    """Represents an Australian Government department with its AI transparency statement."""

    name: str
    slug: str
    url: str


# List of Australian Government departments and their AI Transparency Statement URLs
DEPARTMENTS = [
    Department(
        name="Digital Transformation Agency",
        slug="dta",
        url="https://www.dta.gov.au/ai-transparency-statement",
    ),
    Department(
        name="Treasury",
        slug="treasury",
        url="https://treasury.gov.au/the-department/accountability-reporting/ai-transparency-statement",
    ),
    Department(
        name="Department of Agriculture, Fisheries and Forestry",
        slug="daff",
        url="https://www.agriculture.gov.au/about/reporting/obligations/AI-transparency-statement",
    ),
    Department(
        name="Department of Health and Aged Care",
        slug="health",
        url="https://www.health.gov.au/about-us/corporate-reporting/our-commitments/ai-transparency-statement",
    ),
    Department(
        name="National Indigenous Australians Agency",
        slug="niaa",
        url="https://www.niaa.gov.au/artificial-intelligence-ai-transparency-statement",
    ),
    Department(
        name="Australian Institute of Criminology",
        slug="aic",
        url="https://www.aic.gov.au/about-us/artificial-intelligence-ai-transparency-statement",
    ),
    Department(
        name="Australian Securities and Investments Commission",
        slug="asic",
        url="https://www.asic.gov.au/about-asic/what-we-do/how-we-operate/accountability-and-reporting/artificial-intelligence-transparency-statement/",
    ),
    Department(
        name="Department of Education",
        slug="education",
        url="https://www.education.gov.au/about-department/corporate-reporting/artificial-intelligence-ai-transparency-statement",
    ),
    Department(
        name="Department of Home Affairs",
        slug="homeaffairs",
        url="https://www.homeaffairs.gov.au/commitments/files/ai-transparency-statement.pdf",
    ),
]


def clean_html_to_markdown(html_content: str, base_url: str) -> str:
    """
    Convert HTML content to clean markdown.

    Args:
        html_content: Raw HTML content
        base_url: Base URL for resolving relative links

    Returns:
        Cleaned markdown content
    """
    h = html2text.HTML2Text()
    h.body_width = 0  # Don't wrap lines
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.skip_internal_links = False
    h.baseurl = base_url

    markdown = h.handle(html_content)

    # Clean up excessive newlines
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    return markdown.strip()


def extract_main_content(soup: BeautifulSoup) -> str:
    """
    Extract the main content from the page, removing navigation and footers.

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        HTML string of main content
    """
    # Try to find main content area using common selectors
    main_content = None

    # Try various common main content selectors
    for selector in ["main", "article", ".content", "#content", ".main-content"]:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # If no main content found, use body but remove nav, header, footer
    if not main_content:
        main_content = soup.find("body")
        if main_content:
            for tag in main_content.find_all(["nav", "header", "footer"]):
                tag.decompose()

    return str(main_content) if main_content else str(soup)


def fetch_statement(department: Department) -> dict[str, str | int | None]:
    """
    Fetch and parse an AI transparency statement.

    Args:
        department: Department information

    Returns:
        Dictionary containing parsed content and metadata
    """
    logger.info(f"Fetching {department.name}...")

    try:
        response = httpx.get(
            department.url,
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "AU-Gov-AI-Transparency-Tracker/1.0"},
        )
        response.raise_for_status()

        # Check if content is PDF
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or department.url.endswith(".pdf")

        if is_pdf:
            # Extract text from PDF
            pdf_reader = PdfReader(BytesIO(response.content))

            # Extract title from PDF metadata
            title = None
            if pdf_reader.metadata and pdf_reader.metadata.title:
                title = str(pdf_reader.metadata.title)

            # Extract text from all pages
            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            markdown_content = "\n\n".join(text_parts).strip()

            return {
                "title": title,
                "markdown": markdown_content,
                "last_modified": None,
                "status_code": int(response.status_code),
                "final_url": str(response.url),
                "error": None,
            }
        else:
            # Parse HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Extract title - ensure it's a plain string
            title = None
            if soup.title and soup.title.string:
                title = str(soup.title.string).strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)

            # Extract main content
            main_html = extract_main_content(soup)
            markdown_content = clean_html_to_markdown(main_html, department.url)

            # Extract last modified date if available - ensure it's a plain string
            last_modified = None
            date_meta = soup.find("meta", {"name": "last-modified"})
            if date_meta and date_meta.get("content"):
                last_modified = str(date_meta["content"])

            return {
                "title": str(title) if title else None,
                "markdown": markdown_content,
                "last_modified": last_modified,
                "status_code": int(response.status_code),
                "final_url": str(response.url),
                "error": None,
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching {department.name}: {e}")
        return {
            "title": None,
            "markdown": None,
            "last_modified": None,
            "status_code": e.response.status_code,
            "final_url": department.url,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Error fetching {department.name}: {e}")
        return {
            "title": None,
            "markdown": None,
            "last_modified": None,
            "status_code": None,
            "final_url": department.url,
            "error": str(e),
        }


def save_statement(
    department: Department, data: dict[str, str | int | None], output_dir: Path
) -> None:
    """
    Save statement as markdown file with YAML frontmatter.

    Args:
        department: Department information
        data: Parsed statement data
        output_dir: Directory to save files
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{department.slug}.md"
    filepath = output_dir / filename

    # Prepare frontmatter (ensure all values are serializable)
    frontmatter = {
        "department": department.name,
        "slug": department.slug,
        "source_url": department.url,
        "final_url": str(data["final_url"]) if data["final_url"] else None,
        "fetched_at": datetime.now(UTC).isoformat(),
        "title": data["title"],
        "last_modified": data["last_modified"],
        "status_code": data["status_code"],
        "error": data["error"],
    }

    # Build file content
    content_parts = ["---"]
    content_parts.append(
        yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    )
    content_parts.append("---")
    content_parts.append("")

    if data["markdown"]:
        content_parts.append(data["markdown"])
    elif data["error"]:
        content_parts.append(f"# Error fetching statement\n\n{data['error']}")
    else:
        content_parts.append("# No content available")

    content = "\n".join(content_parts)

    # Write file
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Saved {filename}")


def main() -> int:
    """Main execution function."""
    output_dir = Path(__file__).parent / "statements"

    logger.info(
        f"Starting AI Transparency Statement scrape at {datetime.now(UTC).isoformat()}"
    )
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Processing {len(DEPARTMENTS)} departments")

    success_count = 0
    error_count = 0

    for department in DEPARTMENTS:
        data = fetch_statement(department)
        save_statement(department, data, output_dir)

        if data["error"]:
            error_count += 1
        else:
            success_count += 1

    logger.info(f"Completed: {success_count} successful, {error_count} errors")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
