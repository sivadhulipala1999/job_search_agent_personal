"""
CLI entrypoint parsing.
"""

import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="Job Search Agent CLI")
    parser.add_argument(
        "--cv", type=str, required=True, help="Path to your CV in PDF format"
    )
    parser.add_argument(
        "--country", type=str, required=True, help="Target country for the job search"
    )
    parser.add_argument(
        "--results-per-keyword",
        type=int,
        default=10,
        help="Number of jobs to retrieve per keyword",
    )
    return parser.parse_args()
