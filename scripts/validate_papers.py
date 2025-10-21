import re
import sys
import datetime as dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "papers.yml"


def error(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg: str):
    print(f"WARN: {msg}")


def is_iso_date(s: str) -> bool:
    try:
        dt.date.fromisoformat(s)
        return True
    except Exception:
        return False


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s or ""))


def main() -> int:
    if not DATA.exists():
        error(f"missing {DATA}")
        return 1
    try:
        items = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    except Exception as e:
        error(f"failed to parse YAML: {e}")
        return 1

    if not isinstance(items, list):
        error("top-level YAML must be a list")
        return 1

    errors = 0
    seen_link = set()
    seen_title_date = set()
    allowed_keys = {"title", "category", "date", "link", "note"}

    for i, obj in enumerate(items, start=1):
        if not isinstance(obj, dict):
            error(f"item #{i} must be a mapping")
            errors += 1
            continue

        unknown = set(obj.keys()) - allowed_keys
        if unknown:
            warn(f"item #{i}: unknown keys {sorted(unknown)} (will be ignored)")

        title = obj.get("title")
        category = obj.get("category")
        date = obj.get("date")
        link = obj.get("link")

        if not isinstance(title, str) or not title.strip():
            error(f"item #{i}: missing or empty 'title'")
            errors += 1
        if not isinstance(category, str) or not category.strip():
            error(f"item #{i}: missing or empty 'category'")
            errors += 1
        if not isinstance(date, str) or not is_iso_date(date):
            error(f"item #{i}: 'date' must be ISO YYYY-MM-DD")
            errors += 1
        if not isinstance(link, str) or not is_url(link):
            error(f"item #{i}: 'link' must be an http(s) URL")
            errors += 1

        # Duplicate detection (warnings only)
        if isinstance(link, str) and link:
            if link in seen_link:
                warn(f"item #{i}: duplicate link {link}")
            seen_link.add(link)
        key = (title or "", date or "")
        if all(key):
            if key in seen_title_date:
                warn(f"item #{i}: duplicate title+date {key}")
            seen_title_date.add(key)

        note = obj.get("note")
        if note is not None and not isinstance(note, str):
            error(f"item #{i}: 'note' must be a string if present")
            errors += 1

    if errors:
        error(f"validation failed with {errors} error(s)")
        return 1
    print(f"Validated {len(items)} entries successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

