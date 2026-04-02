"""
Tests for main module.
"""

from job_search_agent.main import hello_world

def test_hello_world():
    """Verify hello_world function."""
    assert hello_world() == "Hello from Job Search Agent!"
