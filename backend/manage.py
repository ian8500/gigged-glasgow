from __future__ import annotations

import argparse

from app.db.schema import create_or_update_local_schema
from app.db.session import engine, SessionLocal
from app.models import artist, city, city_brand, event, source, social_post, venue, venue_check_log, weekly_issue  # noqa: F401
from app.services.deduplication import dedupe_city
from app.services.ingestion import ingest_city
from app.services.seed import seed_glasgow
from app.services.social_generation import generate_social_posts
from app.services.weekly import generate_weekly_issue


def init_db() -> None:
    create_or_update_local_schema(engine)


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        seed_glasgow(db)


def ingest(city_slug: str) -> None:
    init_db()
    with SessionLocal() as db:
        report = ingest_city(db, city_slug)
    print(
        f"Ingested {report.city}: fetched={report.fetched}, created={report.created}, "
        f"updated={report.updated}, skipped={report.skipped}"
    )
    for warning in report.warnings:
        print(f"warning: {warning}")


def dedupe(city_slug: str) -> None:
    init_db()
    with SessionLocal() as db:
        report = dedupe_city(db, city_slug)
    print(
        f"Deduped {report.city}: reviewed={report.reviewed}, merged={report.merged}, "
        f"updated_fingerprints={report.updated_fingerprints}"
    )


def generate_weekly(city_slug: str) -> None:
    init_db()
    with SessionLocal() as db:
        report = generate_weekly_issue(db, city_slug)
    print(
        f"Generated weekly issue {report.issue_slug}: events_selected={report.events_selected}, "
        f"post_created={report.post_created}"
    )
    print(f"coverage: {report.coverage_report.get('explanation', 'coverage report unavailable')}")


def generate_social(city_slug: str) -> None:
    init_db()
    with SessionLocal() as db:
        report = generate_social_posts(db, city_slug)
    print(
        f"Generated social drafts for {report.city}: generated={report.generated}, "
        f"post_ids={','.join(str(post_id) for post_id in report.post_ids)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Gigged Glasgow backend management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create local SQLite tables")
    subparsers.add_parser("seed", help="Seed Glasgow city and venue data")
    ingest_parser = subparsers.add_parser("ingest", help="Ingest events from configured sources")
    ingest_parser.add_argument("--city", default="glasgow", help="City slug to ingest")
    dedupe_parser = subparsers.add_parser("dedupe", help="Deduplicate normalised events")
    dedupe_parser.add_argument("--city", default="glasgow", help="City slug to deduplicate")
    weekly_parser = subparsers.add_parser("generate-weekly", help="Create weekly issue and social draft")
    weekly_parser.add_argument("--city", default="glasgow", help="City slug to generate")
    social_parser = subparsers.add_parser("generate-social", help="Create Instagram drafts for review")
    social_parser.add_argument("--city", default="glasgow", help="City slug to generate")

    args = parser.parse_args()
    if args.command == "init-db":
        init_db()
    if args.command == "seed":
        seed()
    if args.command == "ingest":
        ingest(args.city)
    if args.command == "dedupe":
        dedupe(args.city)
    if args.command == "generate-weekly":
        generate_weekly(args.city)
    if args.command == "generate-social":
        generate_social(args.city)


if __name__ == "__main__":
    main()
