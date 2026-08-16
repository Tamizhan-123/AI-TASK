"""
Ingestion for the Week 3 billing-migration help-centre drop.

Scope note (required by the task): this run indexes ONLY the 6 new articles
under articles/. It does NOT re-index, read, or reference any historical
article corpus. That constraint is enforced simply by pointing ARTICLES_DIR
at the new-drop folder only -- there is no historical corpus wired into this
pipeline at all.
"""

import os
import re

ARTICLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "articles")

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


class IngestError(Exception):
    pass


def _parse_frontmatter(raw_text, source_file):
    match = FRONTMATTER_RE.match(raw_text)
    if not match:
        raise IngestError(f"{source_file}: no frontmatter block found")
    fm_block, body = match.group(1), match.group(2)

    meta = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta, body.strip()


def build_record(source_file, meta, body):
    """
    Build a single ingest record. Raises IngestError if source_file is
    missing/empty -- per the task spec, a record with no source_file is a
    failed ingest and must be raised/logged, never silently indexed.
    """
    if not source_file:
        raise IngestError("record has no source_file -- failed ingest")

    for required_field in ("article_id", "product_area", "last_updated"):
        if required_field not in meta or not meta[required_field]:
            raise IngestError(
                f"{source_file}: missing required frontmatter field '{required_field}'"
            )

    return {
        "source_file": source_file,
        "article_id": meta["article_id"],
        "product_area": meta["product_area"],
        "last_updated": meta["last_updated"],
        "body": body,
    }


def ingest_articles(articles_dir=ARTICLES_DIR):
    """
    Parse every .md file in articles_dir into a record. Returns
    (records, failures) where failures is a list of (filename, error_message).
    """
    records = []
    failures = []

    filenames = sorted(f for f in os.listdir(articles_dir) if f.endswith(".md"))

    for filename in filenames:
        path = os.path.join(articles_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw_text = fh.read()
            meta, body = _parse_frontmatter(raw_text, filename)
            record = build_record(filename, meta, body)
            records.append(record)
        except IngestError as exc:
            failures.append((filename, str(exc)))

    return records, failures


def _selftest_missing_source_file_guard():
    """
    Demonstrates that the missing-source_file guard actually fires, using a
    synthetic bad record. This does not touch the real 6-article ingest
    count above -- it's a guard self-test surfaced in the ingest report.
    """
    try:
        build_record(
            source_file=None,
            meta={"article_id": "X", "product_area": "x", "last_updated": "x"},
            body="unused",
        )
        return "FAIL: guard did not raise for missing source_file"
    except IngestError as exc:
        return f"OK: guard raised as expected -> {exc}"


def print_ingest_report(records, failures):
    print("=" * 70)
    print("INGEST REPORT")
    print("=" * 70)
    print(
        "Scope: indexing ONLY the 6 new billing-migration articles in "
        "articles/. The historical article corpus is NOT touched by this run."
    )
    print(f"Articles directory: {ARTICLES_DIR}")
    print(f"Successful records: {len(records)}")
    for rec in records:
        print(
            f"  - {rec['source_file']:<35} article_id={rec['article_id']:<12} "
            f"product_area={rec['product_area']:<10} last_updated={rec['last_updated']}"
        )
    print(f"Failed records: {len(failures)}")
    for filename, err in failures:
        print(f"  - {filename}: {err}")
    print(f"Guard self-test (missing source_file): {_selftest_missing_source_file_guard()}")
    print("=" * 70)


if __name__ == "__main__":
    recs, fails = ingest_articles()
    print_ingest_report(recs, fails)
