"""Bulk-ingest unregistered PDFs from data/documents."""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.services.document_service import DocumentService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", help="Optional category applied to every new PDF")
    args = parser.parse_args()
    service = DocumentService()
    paths = sorted(get_settings().documents_dir.glob("*.pdf"))
    if not paths:
        print("No PDFs found in data/documents.")
        return 0
    failures = 0
    for path in paths:
        try:
            category = args.category or next(
                (name for name in ("Attendance", "Examination", "Placement", "Internship") if name.lower() in path.stem.lower()),
                "Other",
            )
            result = service.ingest_path(path, category=category)
            print(f"Indexed {result.title}: {result.page_count} pages, {result.chunk_count} chunks")
        except Exception as exc:
            failures += 1
            print(f"FAILED {path.name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
