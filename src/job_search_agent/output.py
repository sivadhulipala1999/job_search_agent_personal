import os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

def generate_markdown_report(keywords: List[str], jobs: List[Dict[str, Any]], output_dir: str = None, filename: str = None) -> str:
    """Generates a markdown report of curated jobs."""
    if not filename:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"curated_list_{date_str}.md"
    
    if not output_dir:
        output_dir = Path(__file__).resolve().parent.parent.parent
        
    filepath = Path(output_dir) / filename
    
    # Sort jobs by status (New vs Repeated) and then score descending
    new_jobs = sorted([j for j in jobs if j.get('status') == 'New'], key=lambda x: x.get("score", 0), reverse=True)
    repeated_jobs = sorted([j for j in jobs if j.get('status') == 'Repeated'], key=lambda x: x.get("score", 0), reverse=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 🤖 AI Job Search Agent - Daily Curated List\n\n")
        f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Active Search Keywords:** {', '.join(keywords)}\n\n")
        
        f.write("## 🚀 New Jobs\n\n")
        if not new_jobs:
            f.write("*No highly relevant new jobs found today.*\n\n")
        else:
            for i, job in enumerate(new_jobs, 1):
                f.write(f"### {i}. {job.get('title', 'Unknown Title')} ({job.get('score', 0)}% Profile Match)\n")
                f.write(f"- **Company:** {job.get('company', 'Unknown')}\n")
                f.write(f"- **Location:** {job.get('location', 'Unknown')}\n")
                f.write(f"- **Salary:** {job.get('salary', 'Not Disclosed')}\n")
                f.write(f"- **Source URL:** {job.get('url', 'No Link')}\n")
                f.write(f"- **AI Reasoning:** {job.get('reasoning', '')}\n")
                f.write(f"- **Description Snippet:** {job.get('description', '')[:300]}...\n\n")
                f.write("---\n\n")
                
        f.write("## ♻️ Repeated Jobs (Still Active)\n\n")
        if not repeated_jobs:
            f.write("*No repeated highly relevant jobs processed today.*\n\n")
        else:
            for i, job in enumerate(repeated_jobs, 1):
                f.write(f"### {i}. {job.get('title', 'Unknown Title')} ({job.get('score', 0)}% Profile Match)\n")
                f.write(f"- **Company:** {job.get('company', 'Unknown')}\n")
                f.write(f"- **Location:** {job.get('location', 'Unknown')}\n")
                f.write(f"- **Salary:** {job.get('salary', 'Not Disclosed')}\n")
                f.write(f"- **Source URL:** {job.get('url', 'No Link')}\n")
                f.write(f"- **AI Reasoning:** {job.get('reasoning', '')}\n")
                f.write("---\n\n")

    return str(filepath)
