"""Core scraping functionality for AI transparency statements."""

import logging
import re
import tomllib
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import html2text
import httpx
import yaml
from bs4 import BeautifulSoup
from pypdf import PdfReader

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Agency(NamedTuple):
    """Represents an Australian Government agency with its AI transparency statement."""

    name: str
    slug: str
    url: str


def load_agencies() -> list[Agency]:
    """
    Load agency data from agencies.toml file.

    Returns:
        List of Agency objects
    """
    toml_path = Path(__file__).parent.parent.parent / "agencies.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    return [
        Agency(name=d["name"], slug=d["slug"], url=d["url"]) for d in data["agencies"]
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


def fetch_statement(agency: Agency) -> dict[str, str | int | None]:
    """
    Fetch and parse an AI transparency statement.

    Args:
        agency: Agency information

    Returns:
        Dictionary containing parsed content and metadata
    """
    logger.info(f"Fetching {agency.name}...")

    try:
        response = httpx.get(
            agency.url,
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "AU-Gov-AI-Transparency-Tracker/1.0"},
        )
        response.raise_for_status()

        # Check if content is PDF
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or agency.url.endswith(".pdf")

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
            markdown_content = clean_html_to_markdown(main_html, agency.url)

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
        logger.error(f"HTTP error fetching {agency.name}: {e}")
        return {
            "title": None,
            "markdown": None,
            "last_modified": None,
            "status_code": e.response.status_code,
            "final_url": agency.url,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Error fetching {agency.name}: {e}")
        return {
            "title": None,
            "markdown": None,
            "last_modified": None,
            "status_code": None,
            "final_url": agency.url,
            "error": str(e),
        }


def save_statement(
    agency: Agency, data: dict[str, str | int | None], output_dir: Path
) -> bool:
    """
    Save statement as markdown file with YAML frontmatter.

    Args:
        agency: Agency information
        data: Parsed statement data
        output_dir: Directory to save files

    Returns:
        True if file was saved, False if skipped due to error
    """
    # Skip saving if there was an error
    if data["error"] or not data["markdown"]:
        logger.warning(f"Skipping {agency.slug} due to fetch error")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{agency.slug}.md"
    filepath = output_dir / filename

    # Prepare minimal frontmatter
    frontmatter = {
        "agency": agency.name,
        "slug": agency.slug,
        "source_url": agency.url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "title": data["title"],
    }

    # Only include final_url if it differs from source_url (redirects)
    if data["final_url"] and data["final_url"] != agency.url:
        frontmatter["final_url"] = str(data["final_url"])

    # Build file content
    content_parts = ["---"]
    content_parts.append(
        yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()
    )
    content_parts.append("---")
    content_parts.append("")
    content_parts.append(data["markdown"])

    content = "\n".join(content_parts)

    # Write file
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Saved {filename}")
    return True
