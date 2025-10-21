import datetime
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplcyberpunk
import numpy as np
import yaml
from matplotlib.patches import FancyBboxPatch
import re

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = ROOT / "assets"
MARK_START = "<!--CHART_START-->"
MARK_END = "<!--CHART_END-->"

# Prefer standard library zoneinfo (Python 3.9+). If unavailable or TZ invalid,
# gracefully fall back to the system local date.
try:  # Python >=3.9
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:  # pragma: no cover - older Python
    ZoneInfo = None  # type: ignore


def today_in_tz() -> datetime.date:
    """
    Return today's date in the configured timezone.

    - Uses env var `PAPERS_TZ` if set (e.g., "Asia/Tokyo").
    - Otherwise uses `TZ` if set (common on Linux/macOS).
    - Falls back to system local date if zoneinfo or TZ is unavailable.
    """
    tz_name = os.environ.get("PAPERS_TZ") or os.environ.get("TZ")
    if tz_name and ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
            return datetime.datetime.now(tz).date()
        except Exception:
            pass
    # Fallback: system local date (GitHub Hosted runners default to UTC)
    return datetime.date.today()


# Matplotlib: enforce deterministic SVGs and consistent fonts across environments.
# - DejaVu Sans is bundled with Matplotlib, avoiding host font differences
# - Convert SVG text to paths and fix SVG hashsalt for reproducible ids
mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.sans-serif": ["DejaVu Sans"],
        "axes.unicode_minus": False,
        "svg.fonttype": "path",  # outline text -> no runtime font dependency
        "svg.hashsalt": "paper-readings-fixed-hash",  # stable element ids
    }
)


def load_papers():
    with open(ROOT / "data" / "papers.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def make_bar_chart_stylish(counts, outpath: Path):
    plt.style.use("cyberpunk")
    # Re-apply font settings after style, in case style overrides fonts
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans"],
        }
    )

    ASSETS.mkdir(parents=True, exist_ok=True)
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    cats = [k for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=200)

    bars = ax.barh(cats, vals, height=0.6, linewidth=0)
    mplcyberpunk.add_bar_gradient(bars=bars, horizontal=True)

    for y, v in enumerate(vals):
        ax.text(
            v + max(vals) * 0.02,
            y,
            str(v),
            va="center",
            ha="left",
            fontsize=11,
        )

    ax.invert_yaxis()
    ax.grid(axis="x", linewidth=1, alpha=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Count", labelpad=8)
    ax.set_title("Papers by Category", pad=12, fontsize=14, weight="bold")

    plt.tight_layout()
    fig.savefig(outpath, format=outpath.suffix.lstrip("."), bbox_inches="tight")
    plt.close(fig)
    _normalize_svg_metadata(outpath)


def parse_date(date_str: str):
    try:
        return datetime.date.fromisoformat(date_str)
    except Exception:
        return None


def custom_cmap(value):
    value = int(max(0, min(value, 5)))
    match value:
        case 0:
            return "#888888"
        case 1:
            return "#1c526b"
        case 2:
            return "#177b90"
        case 3:
            return "#12a5b5"
        case 4:
            return "#0dceda"
        case 5:
            return "#08f7fe"
        case _:
            return "#ffffff"


def make_calendar_heatmap(papers, outpath: Path):
    ASSETS.mkdir(parents=True, exist_ok=True)

    # Use timezone-aware "today" so the heatmap reflects the desired local day
    # (e.g., Asia/Tokyo) instead of the runner's system timezone.
    today = today_in_tz()
    start = today - datetime.timedelta(days=364)

    per_day = defaultdict(int)
    for p in papers:
        d = parse_date(p.get("date", ""))
        if d and start <= d <= today:
            per_day[d] += 1

    days_to_prev_sun = (start.weekday() + 1) % 7
    grid_start = start - datetime.timedelta(days=days_to_prev_sun)

    n_weeks = 53
    n_days = 7

    data = np.zeros((n_days, n_weeks), dtype=float)
    in_range_mask = np.zeros_like(data, dtype=bool)

    week_starts = []
    d = grid_start
    for w in range(n_weeks):
        week_starts.append(d)
        for dow in range(n_days):  # 0:Sun ... 6:Sat
            dd = d + datetime.timedelta(days=dow)
            if start <= dd <= today:
                data[dow, w] = per_day.get(dd, 0)
                in_range_mask[dow, w] = True
            else:
                data[dow, w] = np.nan
        d += datetime.timedelta(days=7)

    fig, ax = plt.subplots(figsize=(8, 2.0), dpi=200)

    cell_pad = 0.15  # gap around each square (in cell units)
    rounding = 0.25  # rounded corner radius (in cell units)
    w = 1 - 2 * cell_pad
    h = 1 - 2 * cell_pad

    for row in range(n_days):
        for col in range(n_weeks):
            val = data[row, col]
            if np.isnan(val):
                continue  # outside range: skip drawing
            # 0-count days use a light gray like GitHub; >0 use colormap
            face = custom_cmap(val)
            # Place a slightly smaller rounded rectangle to create gutters
            x0 = col + cell_pad
            y0 = row + cell_pad
            patch = FancyBboxPatch(
                (x0, y0),
                w,
                h,
                boxstyle=f"round,pad=0,rounding_size={rounding}",
                linewidth=0,  # no stroke like GitHub
                facecolor=face,
                antialiased=True,
            )
            ax.add_patch(patch)

    # legends
    x_legend = x0 - 2
    y_legend = y0 + 2
    for v in range(5, -1, -1):
        patch = FancyBboxPatch(
            (x_legend, y_legend),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={rounding}",
            linewidth=0,  # no stroke like GitHub
            facecolor=custom_cmap(v),
            antialiased=True,
        )
        ax.add_patch(patch)
        x_legend -= 1

    ax.text(
        0.97,
        0.05,
        "More",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8,
        color="#eeeeee",
    )
    ax.text(
        0.805,
        0.05,
        "Less",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=8,
        color="#eeeeee",
    )

    ax.set_xlim(0, n_weeks)
    ax.set_ylim(n_days + 2, 0)  # invert y-axis
    ax.set_aspect("equal")

    ax.set_yticks([1.5, 3.5, 5.5])
    ax.set_yticklabels(["Mon", "Wed", "Fri"], fontsize=8, color="#eeeeee")
    ax.set_xticks([])
    ax.tick_params(bottom=False, left=False)
    ax.grid(False)
    # Remove outer frame (spines)
    for spine in ax.spines.values():
        spine.set_visible(False)

    month_positions = []
    month_labels = []
    last_month = None
    for col, ws in enumerate(week_starts):
        mon = (ws.year, ws.month)
        if not np.any(in_range_mask[:, col]):
            continue
        if mon != last_month and col > 0:
            month_positions.append(col + 0.5)
            month_labels.append(ws.strftime("%b"))  # Jan, Feb, ...
            last_month = mon

    for xpos, lab in zip(month_positions, month_labels):
        ax.text(xpos, -0.35, lab, ha="center", va="bottom", fontsize=8, color="#eeeeee")

    n_papers = sum(per_day.values())
    ax.set_title(
        f"{n_papers} papers read in the last 12 months",
        fontsize=12,
        pad=20,
        weight="bold",
    )

    plt.tight_layout()
    fig.savefig(outpath, format=outpath.suffix.lstrip("."), bbox_inches="tight")
    plt.close(fig)
    _normalize_svg_metadata(outpath)


def _normalize_svg_metadata(svg_path: Path):
    """Make SVG deterministic by removing volatile metadata like timestamps.

    - Replace <dc:date>...</dc:date> with a fixed epoch.
    """
    try:
        text = svg_path.read_text(encoding="utf-8")
        text = re.sub(
            r"<dc:date>.*?</dc:date>", "<dc:date>1970-01-01T00:00:00</dc:date>", text
        )
        svg_path.write_text(text, encoding="utf-8")
    except Exception:
        # Best-effort; ignore if anything goes wrong.
        pass


def render_table_md(counts, total):
    lines = ["\n**Breakdown**", "", "| Category | Count |", "|---|---|"]
    for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        lines.append(f"| {k} | {v} |")
    lines.append(f"| **Total** | **{total}** |")
    return "\n".join(lines)


def make_recent_list_md(papers, limit=10):
    def pd(d):
        try:
            return datetime.date.fromisoformat(d)
        except Exception:
            return datetime.date.min

    s = sorted(papers, key=lambda p: pd(p.get("date", "")), reverse=True)
    items = []
    for p in s[:limit]:
        t, c, d, link = (
            p.get("title", "(no title)"),
            p.get("category", "-"),
            p.get("date", ""),
            p.get("link", ""),
        )
        items.append(
            f"- [{t}]({link}) — *{c}* ({d})" if link else f"- {t} — *{c}* ({d})"
        )
    return "\n".join(["\n**Recently read**", ""] + items) if items else ""


def update_readme(chart1_rel, chart2_rel, table_md, recent_md):
    md = README.read_text(encoding="utf-8")
    start = md.find(MARK_START)
    end = md.find(MARK_END)
    if start == -1 or end == -1 or end < start:
        raise RuntimeError("Markers not found in README.md")
    insert_md = "\n".join(
        [
            f"![By category]({chart1_rel})",
            "",
            f"![Activity heatmap]({chart2_rel})",
            "",
            table_md,
            recent_md,
        ]
    )
    new_md = md[: start + len(MARK_START)] + "\n" + insert_md + "\n" + md[end:]
    README.write_text(new_md, encoding="utf-8")


def main():
    papers = load_papers()
    counts = Counter([p.get("category", "Unknown") for p in papers])
    total = sum(counts.values())

    ASSETS.mkdir(exist_ok=True, parents=True)
    bar_svg = ASSETS / "category_stylish.svg"
    heat_svg = ASSETS / "activity_heatmap.svg"

    make_bar_chart_stylish(counts, bar_svg)
    make_calendar_heatmap(papers, heat_svg)

    table_md = render_table_md(counts, total)
    recent_md = make_recent_list_md(papers, limit=10)

    update_readme(
        "assets/" + bar_svg.name, "assets/" + heat_svg.name, table_md, recent_md
    )


if __name__ == "__main__":
    main()
