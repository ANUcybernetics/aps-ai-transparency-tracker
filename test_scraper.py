"""
Smoke tests for AI Transparency Statement scraper.

Tests verify basic functionality and invariants without asserting
on external content that may change.

Usage:
    uv run pytest test_scraper.py -v
"""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml
from bs4 import BeautifulSoup

# Add current directory to path to import the main script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scrape_ai_statements import (
    Department,
    clean_html_to_markdown,
    extract_main_content,
    fetch_statement,
    load_departments,
    save_statement,
)


def test_departments_list_structure():
    """Verify departments list has required structure."""
    departments = load_departments()
    assert len(departments) > 0
    for dept in departments:
        assert isinstance(dept, Department)
        assert dept.name
        assert dept.slug
        assert dept.url.startswith("http")


def test_departments_unique_slugs():
    """Ensure all department slugs are unique."""
    departments = load_departments()
    slugs = [d.slug for d in departments]
    assert len(slugs) == len(set(slugs))


def test_clean_html_to_markdown_basic():
    """Test HTML to markdown conversion produces valid output."""
    html = "<h1>Test Title</h1><p>Some content</p>"
    markdown = clean_html_to_markdown(html, "https://example.com")

    assert "Test Title" in markdown
    assert "Some content" in markdown
    assert len(markdown) > 0


def test_clean_html_to_markdown_removes_excess_newlines():
    """Test that excessive newlines are cleaned up."""
    html = "<p>Para 1</p>\n\n\n\n<p>Para 2</p>"
    markdown = clean_html_to_markdown(html, "https://example.com")

    # Should not have more than 2 consecutive newlines
    assert "\n\n\n" not in markdown


def test_extract_main_content_with_main_tag():
    """Test extraction when main tag exists."""
    html = """
    <html>
        <nav>Navigation</nav>
        <main>Main content here</main>
        <footer>Footer</footer>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    content = extract_main_content(soup)

    assert "Main content here" in content
    assert isinstance(content, str)


def test_extract_main_content_fallback():
    """Test extraction falls back to body when no main tag."""
    html = """
    <html>
        <body>
            <nav>Navigation</nav>
            <div>Body content</div>
            <footer>Footer</footer>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    content = extract_main_content(soup)

    assert "Body content" in content
    # Nav and footer should be removed
    assert "Navigation" not in content
    assert "Footer" not in content


def test_fetch_statement_returns_required_fields():
    """Test fetch_statement returns dict with all required fields."""
    departments = load_departments()
    dept = departments[0]
    result = fetch_statement(dept)

    required_fields = {
        "title",
        "markdown",
        "last_modified",
        "status_code",
        "final_url",
        "error",
    }
    assert set(result.keys()) == required_fields


def test_fetch_statement_handles_success():
    """Test successful fetch has expected characteristics."""
    departments = load_departments()
    dept = departments[0]
    result = fetch_statement(dept)

    # Either successful or has error
    if result["error"] is None:
        assert result["status_code"] == 200
        assert result["markdown"] is not None
        assert len(result["markdown"]) > 0
        assert result["final_url"] is not None
    else:
        # If there's an error, status_code might be None or error code
        assert isinstance(result["error"], str)


def test_fetch_statement_type_consistency():
    """Test fetch_statement returns consistent types."""
    departments = load_departments()
    dept = departments[0]
    result = fetch_statement(dept)

    # Check types are consistent
    assert result["title"] is None or isinstance(result["title"], str)
    assert result["markdown"] is None or isinstance(result["markdown"], str)
    assert result["last_modified"] is None or isinstance(result["last_modified"], str)
    assert result["status_code"] is None or isinstance(result["status_code"], int)
    assert isinstance(result["final_url"], str)
    assert result["error"] is None or isinstance(result["error"], str)


def test_save_statement_creates_valid_file():
    """Test save_statement creates properly formatted file."""
    dept = Department(
        name="Test Department", slug="test", url="https://example.com/test"
    )

    data = {
        "title": "Test Statement",
        "markdown": "# Test Content\n\nSome text here.",
        "last_modified": "2024-01-01",
        "status_code": 200,
        "final_url": "https://example.com/test",
        "error": None,
    }

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = save_statement(dept, data, output_dir)

        assert result is True
        filepath = output_dir / "test.md"
        assert filepath.exists()

        content = filepath.read_text()

        # Should start with YAML frontmatter
        assert content.startswith("---\n")

        # Should have closing frontmatter delimiter
        parts = content.split("---\n")
        assert len(parts) >= 3

        # YAML should be valid
        yaml_content = parts[1]
        metadata = yaml.safe_load(yaml_content)
        assert metadata["department"] == "Test Department"
        assert metadata["slug"] == "test"
        assert metadata["source_url"] == "https://example.com/test"
        assert metadata["title"] == "Test Statement"
        assert "fetched_at" in metadata

        # Should not have removed fields
        assert "status_code" not in metadata
        assert "error" not in metadata
        assert "last_modified" not in metadata

        # final_url should not be present when it matches source_url
        assert "final_url" not in metadata

        # Markdown content should be present
        assert "# Test Content" in content


def test_save_statement_handles_error_case():
    """Test save_statement skips file creation when there's an error."""
    dept = Department(
        name="Test Department", slug="test-error", url="https://example.com/test"
    )

    data = {
        "title": None,
        "markdown": None,
        "last_modified": None,
        "status_code": 404,
        "final_url": "https://example.com/test",
        "error": "Not found",
    }

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = save_statement(dept, data, output_dir)

        # Should return False and not create file
        assert result is False
        filepath = output_dir / "test-error.md"
        assert not filepath.exists()


def test_save_statement_handles_no_content():
    """Test save_statement skips file creation when there's no markdown."""
    dept = Department(
        name="Test Department", slug="test-empty", url="https://example.com/test"
    )

    data = {
        "title": None,
        "markdown": None,
        "last_modified": None,
        "status_code": 200,
        "final_url": "https://example.com/test",
        "error": None,
    }

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = save_statement(dept, data, output_dir)

        # Should return False and not create file
        assert result is False
        filepath = output_dir / "test-empty.md"
        assert not filepath.exists()


def test_save_statement_includes_final_url_on_redirect():
    """Test save_statement includes final_url when it differs from source_url."""
    dept = Department(
        name="Test Department", slug="test-redirect", url="https://example.com/old"
    )

    data = {
        "title": "Test Statement",
        "markdown": "# Test Content",
        "last_modified": None,
        "status_code": 200,
        "final_url": "https://example.com/new",
        "error": None,
    }

    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = save_statement(dept, data, output_dir)

        assert result is True
        filepath = output_dir / "test-redirect.md"
        content = filepath.read_text()

        parts = content.split("---\n")
        yaml_content = parts[1]
        metadata = yaml.safe_load(yaml_content)

        # final_url should be present when it differs from source_url
        assert metadata["final_url"] == "https://example.com/new"
        assert metadata["source_url"] == "https://example.com/old"


@pytest.mark.parametrize("dept_index", range(3))
def test_fetch_first_few_departments(dept_index):
    """Integration test: fetch first few departments to verify end-to-end."""
    departments = load_departments()
    if dept_index >= len(departments):
        pytest.skip(f"Only {len(departments)} departments available")

    dept = departments[dept_index]
    result = fetch_statement(dept)

    # Should return valid result structure
    assert isinstance(result, dict)
    assert "error" in result

    # If successful, should have content
    if result["error"] is None:
        assert result["markdown"]
        assert result["status_code"] == 200


def test_all_departments_can_be_fetched():
    """Integration test: verify all departments in departments.toml can be fetched and parsed."""
    departments = load_departments()
    assert len(departments) > 0, "No departments loaded from departments.toml"

    failed_departments = []

    for dept in departments:
        result = fetch_statement(dept)

        # Verify result structure
        assert isinstance(result, dict), f"{dept.slug}: result is not a dict"
        assert "error" in result, f"{dept.slug}: missing 'error' field"

        # Track failures
        if result["error"] is not None:
            failed_departments.append(
                {
                    "name": dept.name,
                    "slug": dept.slug,
                    "url": dept.url,
                    "error": result["error"],
                    "status_code": result["status_code"],
                }
            )
        else:
            # Verify successful fetch has required content
            assert result["status_code"] == 200, f"{dept.slug}: status code not 200"
            assert result["markdown"], f"{dept.slug}: no markdown content"
            assert len(result["markdown"]) > 0, f"{dept.slug}: empty markdown"

    # Report all failures at once
    if failed_departments:
        failure_summary = "\n".join(
            f"  - {f['name']} ({f['slug']}): {f['error']} (status: {f['status_code']})"
            for f in failed_departments
        )
        pytest.fail(
            f"{len(failed_departments)}/{len(departments)} departments failed:\n{failure_summary}"
        )
