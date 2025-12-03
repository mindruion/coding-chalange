# Quorum Coding Challenge – Legislative Data

## Setup
1) Install Python 3.8+.
2) From the repo root:
```bash
pip install -r requirements.txt
```

## Project layout
- `main.py` – Typer CLI with `summarize` and `preview` commands; uses dataclasses for legislators, bills, votes, vote results; renders previews with Rich and Questionary.
- `data/input/` – expected input CSVs: `bills.csv`, `legislators.csv`, `votes.csv`, `vote_results.csv`.
- `data/output/` – default output CSVs: `legislators-support-oppose-count.csv`, `bills-summary.csv`.
- `docs/README.md` – detailed usage guide.
- `docs/WRITEUP.md` – answers to design/complexity questions.
- `docs/pdf/Quorum Coding Challenge Legislative Data.pdf` – provided reference PDF.
- `requirements.txt` – CLI dependencies (Typer, Rich, Questionary).

## Commands (run from repo root)
- Summaries (writes to `data/output/` by default):
  ```bash
  python3 main.py summarize
  ```
  Flags: `--data-dir` (default `data/input`), `--legislator-output`, `--bill-output`.

- Preview (arrow-key selection or direct category):
  ```bash
  python3 main.py preview
  ```
  Flags: `--category` (`bills`, `legislators`, `votes`, `vote_results`, `legislator_summary`, `bill_summary`), `--limit` (rows to show), `--data-dir` (default `data/input`).
  Related IDs are enriched in previews (e.g., bill titles and legislator names).

## Writeup
See `docs/WRITEUP.md` for time/space complexity, tradeoffs, extensibility notes, and effort spent.
