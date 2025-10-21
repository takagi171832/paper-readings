# Use This as a Template

This repository can be used to create your own paper-reading log with automatic charts.

## Quick start

1) Create a new repository using this as a template (GitHub UI: "Use this template").
2) Edit `data/papers.yml` with your entries:

```yaml
- title: "Your paper title"
  category: "LLM"
  date: "YYYY-MM-DD"
  link: "https://..."
  note: "optional short notes"
```

3) Push to your `main` branch. GitHub Actions will render charts and update `README.md`.

## Timezone

The workflow defaults to `Asia/Tokyo`. Change `PAPERS_TZ` in `.github/workflows/update-readme.yml` if needed.

## Validation

The CI validates your `data/papers.yml` format before building charts. Run locally with:

```
uv run scripts/validate_papers.py
```

## License

- Code: MIT (see `LICENSE`)
- Content (your notes/data/charts): CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
