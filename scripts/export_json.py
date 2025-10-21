import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "papers.yml"
OUT = ROOT / "data" / "papers.json"


def main():
    items = yaml.safe_load(IN.read_text(encoding="utf-8")) or []
    # Keep order and unicode; pretty print for readability
    OUT.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(items)} entries)")


if __name__ == "__main__":
    main()

