"""Register reviewed source examples without copying historical jobs into the index."""

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from vindex.connectors.registry import detect
from vindex.db import Session, Source

from scripts.smoke import EXAMPLES

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the reviewed source list")
    args = parser.parse_args()
    providers = json.loads((ROOT / "backend/providers.json").read_text())
    urls = {
        example["url"]
        for provider in providers
        if provider["evidence_status"] == "LIVE_VERIFIED"
        for example in provider["examples"]
        if example["status"] == "LIVE_VERIFIED" and example["complete"]
    }
    # These providers have dedicated smoke/checkpoint runners.
    catalogue = EXAMPLES + [
        ("Jobiqo", "jobiqo", "www.kampajobs.ch", "Kampajobs", "https://www.kampajobs.ch/jobs"),
        (
            "JobMount",
            "jobmount",
            "soudeur.ca",
            "Soudeur.ca",
            "https://soudeur.ca/candidate/job_search/quick/results",
        ),
        (
            "JobMount",
            "jobmount",
            "www.jobsrus.com",
            "JobsRUs",
            "https://www.jobsrus.com/candidate/job_search/quick/results",
        ),
        (
            "Wiley Madgex",
            "wileymadgex",
            "jobs.sciencecareers.org",
            "Science Careers",
            "https://jobs.sciencecareers.org/jobs/",
        ),
        (
            "Wiley Madgex",
            "wileymadgex",
            "www.nature.com",
            "Nature Careers",
            "https://www.nature.com/naturecareers/jobs/",
        ),
    ]
    examples = [example for example in catalogue if example[4] in urls]
    names = {example[0] for example in examples}
    expected = {
        provider["name"] for provider in providers if provider["evidence_status"] == "LIVE_VERIFIED"
    }
    if names != expected:
        raise ValueError("The verified provider inventory and source examples disagree")
    for _, provider, slug, _, url in examples:
        if detect(url) != (provider, slug):
            raise ValueError("A reviewed source URL no longer matches its connector")
    with Session() as session:
        existing = {
            (provider, slug)
            for provider, slug in session.execute(select(Source.provider, Source.slug))
        }
        pending = {
            (provider, slug): Source(provider=provider, slug=slug, company=company, url=url)
            for _, provider, slug, company, url in examples
            if (provider, slug) not in existing
        }
        if args.apply:
            session.add_all(pending.values())
            session.commit()
    print(
        json.dumps(
            {
                "applied": args.apply,
                "verified_platforms": len(names),
                "reviewed_examples": len(examples),
                "new_sources": len(pending),
                "indexing": "Sources are scheduled for a fresh fetch by the running worker",
            }
        )
    )


if __name__ == "__main__":
    main()
