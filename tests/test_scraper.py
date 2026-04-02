
from job_search_agent.scraper import is_title_match


def test_is_title_match_exact():
    """Test if exact keywords are successfully matched."""
    keywords = ["AI Engineer", "Machine Learning"]
    assert is_title_match("AI Engineer", keywords) is True
    assert is_title_match("Senior Machine Learning Developer", keywords) is True


def test_is_title_match_partial_tokens():
    """Test if partial token intersections correctly allow jobs through."""
    keywords = ["Software Engineer"]
    # "Engineer" intersects, so this should pass the filter block
    assert is_title_match("Frontend Engineer", keywords) is True
    assert is_title_match("Senior Software Architect", keywords) is True


def test_is_title_match_failure():
    """Test if unrelated job titles are correctly dropped."""
    keywords = ["Data Scientist", "Analytics"]
    assert is_title_match("AI Engineer", keywords) is False
    assert is_title_match("Chief Technology Officer", keywords) is False


def test_is_title_match_short_tokens():
    """Test that extremely short tokens (len <= 2) like 'AI' are handled carefully."""
    keywords = ["AI Researcher"]
    # The token 'ai' is len 2, so it shouldn't match a random word with 'ai' in it unless exact
    assert is_title_match("Chair Maker", keywords) is False
    # But it does have the full keyword exact substring match test too
    assert is_title_match("Lead AI Researcher", keywords) is True
