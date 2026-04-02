"""
Main application stringing all modules together.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from job_search_agent.extractor import extract_text_from_pdf
from job_search_agent.llm import deduce_keywords_from_cv, score_job_relevance
from job_search_agent.scraper import scrape_jobs_for_keywords


def main():
    import warnings

    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", module="pydantic")

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    load_dotenv(PROJECT_ROOT / ".env")

    country = os.getenv("TARGET_COUNTRY")
    if not country:
        print(
            "Error: TARGET_COUNTRY expects an environment variable. Please define it in your .env or .env.example file."
        )
        sys.exit(1)

    # Standardize reading from the data/cvs/ directory relative to project root
    cv_dir = PROJECT_ROOT / "data" / "cvs"
    cv_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(cv_dir.glob("*.pdf"))
    if not pdf_files:
        print(
            f"Error: No PDF files found in '{cv_dir}'. Please paste your CV in that folder and run again."
        )
        sys.exit(1)

    cv_path = pdf_files[0]

    print(f"Reading CV: {cv_path}")
    try:
        cv_text = extract_text_from_pdf(str(cv_path))
    except Exception as e:
        print(f"Error reading CV: {e}")
        sys.exit(1)

    seed_file = PROJECT_ROOT / "data" / "seed_keywords.json"
    history_file = PROJECT_ROOT / "data" / "history.json"

    # 1. Interactive or Loaded Seed Keywords
    if not seed_file.exists():
        print("Analyzing CV to deduce optimal search keywords for the first time...")
        try:
            seeds = deduce_keywords_from_cv(cv_text)
        except Exception as e:
            print(f"LLM Error (Is your API Key correctly set?): {e}")
            sys.exit(1)

        print(f"Deduced Seed Keywords: {seeds}")
        try:
            user_input = input(
                "Confirm these keywords or provide your own comma-separated list (Press Enter to keep defaults): "
            )
            if user_input.strip():
                seeds = [k.strip() for k in user_input.split(",")]
        except EOFError:
            print("Cron/Non-interactive mode detected. Auto-confirming.")

        with open(seed_file, "w") as f:
            json.dump(seeds, f)
    else:
        with open(seed_file, "r") as f:
            seeds = json.load(f)

    print(f"\nLocked Seed Keywords: {seeds}")

    # 2. Dynamic LLM Expansion
    print("Expanding seeds via LLM to catch variant job titles...")
    from job_search_agent.llm import expand_seed_keywords

    expanded = expand_seed_keywords(seeds, cv_text)
    all_keywords = list(set(seeds + expanded))
    print(f"Active search net: {all_keywords}")

    # 3. Calculate Limits
    max_jobs = int(os.getenv("MAX_JOBS_LIMIT", "50"))
    results_per_kw = max(3, max_jobs // len(all_keywords) if all_keywords else 10)

    print(f"\nScraping job boards for country: {country}...")
    jobs = scrape_jobs_for_keywords(
        all_keywords, country, results_wanted=results_per_kw
    )

    if not jobs:
        print("No jobs found for the deduced keywords.")
        sys.exit(0)

    # 4. History Tracking & Status
    if history_file.exists():
        with open(history_file, "r") as f:
            seen_jobs = set(json.load(f))
    else:
        seen_jobs = set()

    for j in jobs:
        if j["url"] in seen_jobs:
            j["status"] = "Repeated"
        else:
            j["status"] = "New"
            seen_jobs.add(j["url"])

    with open(history_file, "w") as f:
        json.dump(list(seen_jobs), f)

    # 5. Score Jobs
    print(
        f"Extracted {len(jobs)} unique jobs (after local pre-filters). Scoring relevancy using LLM..."
    )
    final_jobs = []

    for i, job in enumerate(jobs):
        sys.stdout.write(
            f"\rScoring [{i+1}/{len(jobs)}]: {job.get('title', '')[:40]:<40}"
        )
        sys.stdout.flush()

        relevance = score_job_relevance(cv_text, job.get("description", ""))
        job["score"] = relevance["score"]
        job["reasoning"] = relevance["reasoning"]

        # 6. Apply strict relevance cutoff
        if job["score"] >= 50:
            final_jobs.append(job)

    print("\nScoring complete!")

    # --- DEBUG DUMP ---
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_path = PROJECT_ROOT / "data" / f"debug_dump_{date_str}.json"
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)
    print(f"Debug JSON dumped to: {debug_path}")

    # 7. Output Generation
    print("Generating curated report...")
    from job_search_agent.output import generate_markdown_report

    # We pass the same date_str to align the files
    report_path = generate_markdown_report(
        all_keywords, final_jobs, filename=f"curated_list_{date_str}.md"
    )
    print(f"Done! Your curated list has been saved to: {report_path}")

    # 8. Post-Processing: Application Assistant
    app_threshold = int(os.getenv("APPLICATION_THRESHOLD", "90"))
    top_jobs = [j for j in final_jobs if j.get("score", 0) >= app_threshold]

    if top_jobs:
        print(
            f"\nFound {len(top_jobs)} jobs exceeding the {app_threshold}% application threshold!"
        )
        print("Generating explicit CV tips and Cover Letters...")
        import re
        from datetime import datetime

        from job_search_agent.llm import generate_application_materials

        apps_dir = PROJECT_ROOT / "data" / "applications"
        apps_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")

        for i, job in enumerate(top_jobs, 1):
            company_clean = re.sub(r"[^a-zA-Z0-9]", "", job.get("company", "Unknown"))
            title_clean = re.sub(r"[^a-zA-Z0-9]", "", job.get("title", "Role"))[:20]

            job_folder = apps_dir / f"{date_str}_{company_clean}_{title_clean}"
            job_folder.mkdir(parents=True, exist_ok=True)

            sys.stdout.write(
                f"\rDrafting Application [{i}/{len(top_jobs)}]: {job.get('company', '')[:30]}"
            )
            sys.stdout.flush()

            materials = generate_application_materials(
                cv_text, job.get("description", "")
            )

            with open(job_folder / "cover_letter.md", "w", encoding="utf-8") as f:
                f.write(materials["cover_letter"])

            with open(job_folder / "cv_recommendations.md", "w", encoding="utf-8") as f:
                f.write(materials["cv_recommendations"])

        print("\nApplication materials generated successfully!")

    # 9. Email Dispatch
    smtp_email = os.getenv("SMTP_EMAIL")
    recipient = os.getenv("RECIPIENT_EMAIL")
    if smtp_email and recipient:
        print("SMTP Credentials found. Dispatching email...")
        from job_search_agent.email_utils import send_report_email

        send_report_email(report_path)


if __name__ == "__main__":
    main()
