import os
from pathlib import Path
from job_search_agent.output import generate_markdown_report

def test_generate_markdown_report(tmp_path):
    """Test output generation specifically handles the New vs Repeated segregration and formats correctly."""
    keywords = ["AI Engineer"]
    jobs = [
        {
            "title": "Data Scientist",
            "company": "OpenAI",
            "location": "Remote",
            "salary": "$200,000",
            "url": "https://example.com/1",
            "description": "Short desc",
            "score": 95,
            "reasoning": "Perfect match",
            "status": "New"
        },
        {
            "title": "Repeated Role",
            "company": "Google",
            "location": "NY",
            "salary": "Not Disclosed",
            "url": "https://example.com/2",
            "description": "Short desc 2",
            "score": 88,
            "reasoning": "Good match",
            "status": "Repeated"
        }
    ]
    
    # Run the generator directing output to our tmp_path directory mock
    output_file = generate_markdown_report(keywords, jobs, output_dir=str(tmp_path), filename="test_curated_list.md")
    
    assert os.path.exists(output_file)
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Validating core formatting structures exist
    assert "## 🚀 New Jobs" in content
    assert "## ♻️ Repeated Jobs (Still Active)" in content
    
    # Validating data interpolation
    assert "Data Scientist" in content
    assert "OpenAI" in content
    assert "$200,000" in content
    assert "95% Profile Match" in content
    assert "Repeated Role" in content
