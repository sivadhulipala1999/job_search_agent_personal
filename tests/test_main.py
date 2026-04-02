from unittest.mock import patch

import pytest

from job_search_agent.main import main


def test_main_missing_target_country_aborts():
    """Test that main() safely intercepts a missing target country env variable and triggers an abort."""
    with patch("os.getenv", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Ensure it exists with a failure code of 1
        assert exc_info.value.code == 1


@patch("os.getenv")
@patch("job_search_agent.main.Path.glob")
def test_main_missing_pdf_aborts(mock_glob, mock_getenv):
    """Test that main() securely aborts if the data/cvs/ folder is entirely empty of PDFs."""
    # Ensure it passes the first barrier
    mock_getenv.return_value = "Germany"

    # Force the PDF blob array to return empty
    mock_glob.return_value = []

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("os.getenv")
@patch("job_search_agent.main.Path.glob")
@patch("job_search_agent.main.extract_text_from_pdf")
def test_main_pdf_read_error_aborts(mock_extract, mock_glob, mock_getenv):
    """Test that main() handles corrupted/unreadable PDFs cleanly."""
    mock_getenv.return_value = "Germany"
    mock_glob.return_value = ["dummy_cv.pdf"]

    # Simulate pdfplumber/pypdf failing on a corrupted file
    mock_extract.side_effect = Exception("Corrupted PDF bytes")

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


@patch("os.getenv")
@patch("pathlib.Path.glob")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
@patch("builtins.open")
@patch("builtins.input", return_value="AI Engineer")
@patch("job_search_agent.main.extract_text_from_pdf", return_value="Mock CV Text")
@patch("job_search_agent.main.deduce_keywords_from_cv", return_value=["AI Engineer"])
@patch("job_search_agent.llm.expand_seed_keywords", return_value=["ML Engineer"])
@patch("job_search_agent.main.scrape_jobs_for_keywords")
@patch("job_search_agent.main.score_job_relevance")
@patch(
    "job_search_agent.output.generate_markdown_report", return_value="fake_report.md"
)
@patch("job_search_agent.llm.generate_application_materials")
@patch("job_search_agent.email_utils.send_report_email")
def test_main_full_successful_pipeline(
    mock_send_email,
    mock_app_mats,
    mock_gen_md,
    mock_score,
    mock_scrape,
    mock_expand,
    mock_deduce,
    mock_extract,
    mock_input,
    mock_open,
    mock_mkdir,
    mock_exists,
    mock_glob,
    mock_getenv,
):
    """Deep Integration test simulating a completely successful execution from end to end."""

    # 1. Setup Environment
    def fake_getenv(key, default=None):
        if key == "TARGET_COUNTRY":
            return "USA"
        if key == "MAX_JOBS_LIMIT":
            return "50"
        if key == "APPLICATION_THRESHOLD":
            return "90"
        if key == "SMTP_EMAIL":
            return "test@test.com"
        if key == "RECIPIENT_EMAIL":
            return "recv@test.com"
        return default

    mock_getenv.side_effect = fake_getenv

    # 2. Mock File System
    mock_glob.return_value = ["fake_cv.pdf"]
    mock_exists.return_value = (
        False  # Forces the script to run seed deduction and new history logs
    )

    # 3. Setup Scraping returns
    mock_scrape.return_value = [
        {
            "title": "AI Engineer",
            "company": "OpenAI",
            "url": "site.com/1",
            "description": "foo",
        }
    ]

    # 4. Setup LLM Scoring & Ghostwriting returns
    mock_score.return_value = {"score": 95, "reasoning": "perfect test match"}
    mock_app_mats.return_value = {
        "cover_letter": "hello",
        "cv_recommendations": "world",
    }

    # Execute the Orchestrator safely
    try:
        main()
    except SystemExit:
        pytest.fail("main() unexpectedly aborted execution!")

    # Assertions validating the Orchestrator successfully routed everything
    mock_extract.assert_called_once()
    mock_deduce.assert_called_once()
    mock_expand.assert_called_once()
    mock_scrape.assert_called_once()
    assert mock_score.call_count == 1
    mock_gen_md.assert_called_once()

    # Since the score is 95, and the threshold is 90, it WILL trigger the application materials
    mock_app_mats.assert_called_once()

    # Since SMTP Email logic is enabled in our mock, it WILL send an email
    mock_send_email.assert_called_once()
