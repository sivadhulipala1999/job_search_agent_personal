"""
Job Scraping module using Meta-Search (DuckDuckGo) with python-jobspy fallback.
"""

from typing import Any, Dict, List

import pandas as pd
from jobspy import scrape_jobs


def is_title_match(job_title: str, keywords: List[str]) -> bool:
    """Pre-filter: Returns True if 'job_title' contains any token from 'keywords' to avoid LLM token waste."""
    title_lower = job_title.lower()
    for kw in keywords:
        tokens = kw.lower().split()
        if any(
            token in title_lower for token in tokens if len(token) > 2
        ):  # ignore tiny words like 'AI' could be tricky but 'AI' is len 2... let's just do > 1
            return True
        # also check exact kw
        if kw.lower() in title_lower:
            return True
    return False


def scrape_with_google_jobs(
    keyword: str, country: str, results_wanted: int
) -> List[Dict[str, Any]]:
    """Primary Scraper: Uses python-jobspy explicitly targeting Google Jobs for cleaner metadata including salary."""
    jobs_list = []
    try:
        jobs_df = scrape_jobs(
            site_name=["google"],
            search_term=keyword,
            location=country,
            results_wanted=results_wanted,
            country_indeed=country,
        )
        if not jobs_df.empty:
            if "job_url" in jobs_df.columns:
                jobs_df = jobs_df.drop_duplicates(subset=["job_url"])

            for _, row in jobs_df.iterrows():
                min_salary = row.get("min_amount")
                max_salary = row.get("max_amount")
                currency = row.get("currency", "")

                # Format Salary
                if pd.notna(min_salary) and pd.notna(max_salary):
                    salary = f"{min_salary}-{max_salary} {currency}".strip()
                elif pd.notna(min_salary):
                    salary = f"{min_salary} {currency}".strip()
                else:
                    salary = "Not Disclosed"

                jobs_list.append(
                    {
                        "title": str(row.get("title", "Unknown Title")),
                        "company": str(row.get("company", "Unknown Company")),
                        "location": str(row.get("location", "Unknown")),
                        "salary": salary,
                        "url": str(row.get("job_url", "")),
                        "description": str(row.get("description", "")),
                        "site": str(row.get("site", "Google Jobs")),
                    }
                )
    except Exception as e:
        print(f"Google Jobs scraper error for '{keyword}': {e}")

    return jobs_list


def scrape_with_jobspy(
    keyword: str, country: str, results_wanted: int
) -> List[Dict[str, Any]]:
    """Legacy python-jobspy fallback logic targeting traditional sites."""
    jobs_list = []
    try:
        jobs_df = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor"],
            search_term=keyword,
            location=country,
            results_wanted=results_wanted,
            country_indeed=country,
        )
        if not jobs_df.empty:
            if "job_url" in jobs_df.columns:
                jobs_df = jobs_df.drop_duplicates(subset=["job_url"])

            for _, row in jobs_df.iterrows():
                min_salary = row.get("min_amount")
                max_salary = row.get("max_amount")
                currency = row.get("currency", "")

                if pd.notna(min_salary) and pd.notna(max_salary):
                    salary = f"{min_salary}-{max_salary} {currency}".strip()
                elif pd.notna(min_salary):
                    salary = f"{min_salary} {currency}".strip()
                else:
                    salary = "Not Disclosed"

                jobs_list.append(
                    {
                        "title": str(row.get("title", "Unknown Title")),
                        "company": str(row.get("company", "Unknown Company")),
                        "location": str(row.get("location", "Unknown")),
                        "salary": salary,
                        "url": str(row.get("job_url", "")),
                        "description": str(row.get("description", "")),
                        "site": str(row.get("site", "")),
                    }
                )
    except Exception as e:
        print(f"Fallback scraper error for '{keyword}': {e}")

    return jobs_list


def scrape_jobs_for_keywords(
    keywords: List[str], country: str, results_wanted: int = 15
) -> List[Dict[str, Any]]:
    """Master orchestration function executing Google Jobs and applying Title Pre-filters."""
    all_jobs = []
    seen_urls = set()

    for word in keywords:
        print(f"Executing Google Jobs Search for '{word}'...")
        # 1. Primary Scrape
        jobs = scrape_with_google_jobs(word, country, results_wanted)

        # 2. Fallback if strictly 0 results
        if not jobs:
            print(
                f"Google Jobs yielded 0 results for '{word}'. Engaging Legacy Fallback..."
            )
            jobs = scrape_with_jobspy(word, country, results_wanted)

        # 3. Filter and Deduplicate
        for job in jobs:
            if job["url"] not in seen_urls:
                # Apply Title Pre-filter
                if is_title_match(job["title"], keywords):
                    seen_urls.add(job["url"])
                    all_jobs.append(job)

    return all_jobs
