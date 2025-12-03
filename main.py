"""
Compute legislator and bill vote summaries from CSV inputs.

Provides two commands:
- summarize: writes legislators-support-oppose-count.csv and bills-summary.csv
- preview: interactively preview the first rows of any input CSV.
Defaults read input CSVs from data/input/ and write outputs to data/output/.
"""

import csv
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

import questionary
import typer
from rich.console import Console
from rich.table import Table

DEFAULT_DATA_DIR = Path("data/input")
DEFAULT_OUTPUT_DIR = Path("data/output")

# Default output filenames
LEGISLATOR_OUTPUT = DEFAULT_OUTPUT_DIR / "legislators-support-oppose-count.csv"
BILL_OUTPUT = DEFAULT_OUTPUT_DIR / "bills-summary.csv"

DATASETS = {
    "bills": "bills.csv",
    "legislators": "legislators.csv",
    "votes": "votes.csv",
    "vote_results": "vote_results.csv",
}

COMPUTED_PREVIEWS = {
    "legislator_summary": "Legislator summary (computed)",
    "bill_summary": "Bill summary (computed)",
}

console = Console()
app = typer.Typer(help="Compute legislative summaries or preview the input CSVs.")


@dataclass
class Legislator:
    id: int
    name: str


@dataclass
class Bill:
    id: int
    title: str
    sponsor_id: Optional[int]


@dataclass
class Vote:
    id: int
    bill_id: int


@dataclass
class VoteResult:
    legislator_id: int
    vote_id: int
    vote_type: int


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse a string to int, returning None on failure."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def read_csv(path: Path) -> Iterable[Dict[str, str]]:
    """Yield rows from a CSV file as dictionaries."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def load_legislators(path: Path) -> List[Legislator]:
    """Return Legislator objects from legislators.csv."""
    legislators: List[Legislator] = []
    for row in read_csv(path):
        leg_id = parse_int(row.get("id"))
        if leg_id is None:
            continue
        legislators.append(Legislator(id=leg_id, name=row.get("name", "").strip()))
    return legislators


def load_bills(path: Path) -> List[Bill]:
    """Return Bill objects from bills.csv."""
    bills: List[Bill] = []
    for row in read_csv(path):
        bill_id = parse_int(row.get("id"))
        if bill_id is None:
            continue

        sponsor_id_raw = (
            row.get("Primary Sponsor")
            or row.get("primary_sponsor")
            or row.get("sponsor_id")
        )
        sponsor_id = parse_int(sponsor_id_raw)
        bills.append(
            Bill(
                id=bill_id,
                title=row.get("title", "").strip(),
                sponsor_id=sponsor_id,
            )
        )
    return bills


def load_votes(path: Path) -> Dict[int, Vote]:
    """Return mapping from vote id to Vote."""
    votes: Dict[int, Vote] = {}
    for row in read_csv(path):
        vote_id = parse_int(row.get("id"))
        bill_id = parse_int(row.get("bill_id"))
        if vote_id is None or bill_id is None:
            continue
        votes[vote_id] = Vote(id=vote_id, bill_id=bill_id)
    return votes


def load_vote_results(path: Path) -> List[VoteResult]:
    """Return VoteResult rows from vote_results.csv."""
    results: List[VoteResult] = []
    for row in read_csv(path):
        legislator_id = parse_int(row.get("legislator_id"))
        vote_id = parse_int(row.get("vote_id"))
        vote_type = parse_int(row.get("vote_type"))
        if legislator_id is None or vote_id is None or vote_type is None:
            continue
        results.append(
            VoteResult(
                legislator_id=legislator_id, vote_id=vote_id, vote_type=vote_type
            )
        )
    return results


def compute_legislator_summary(
    legislators: Sequence[Legislator],
    vote_results: Sequence[VoteResult],
    votes: Dict[int, Vote],
) -> List[Dict[str, object]]:
    """Compute per-legislator support and oppose counts."""
    supported: Dict[int, Set[int]] = {}
    opposed: Dict[int, Set[int]] = {}

    for result in vote_results:
        vote = votes.get(result.vote_id)
        if vote is None:
            continue
        if result.vote_type == 1:
            supported.setdefault(result.legislator_id, set()).add(vote.bill_id)
        elif result.vote_type == 2:
            opposed.setdefault(result.legislator_id, set()).add(vote.bill_id)

    summary: List[Dict[str, object]] = []
    for legislator in sorted(legislators, key=lambda l: l.id):
        summary.append(
            {
                "id": legislator.id,
                "name": legislator.name,
                "num_supported_bills": len(supported.get(legislator.id, set())),
                "num_opposed_bills": len(opposed.get(legislator.id, set())),
            }
        )
    return summary


def compute_bill_summary(
    bills: Sequence[Bill],
    legislators: Sequence[Legislator],
    vote_results: Sequence[VoteResult],
    votes: Dict[int, Vote],
) -> List[Dict[str, object]]:
    """Compute per-bill supporter/opposer counts and sponsor name."""
    supporters: Dict[int, Set[int]] = {}
    opposers: Dict[int, Set[int]] = {}

    for result in vote_results:
        vote = votes.get(result.vote_id)
        if vote is None:
            continue
        if result.vote_type == 1:
            supporters.setdefault(vote.bill_id, set()).add(result.legislator_id)
        elif result.vote_type == 2:
            opposers.setdefault(vote.bill_id, set()).add(result.legislator_id)

    legislator_by_id = {leg.id: leg for leg in legislators}

    summary: List[Dict[str, object]] = []
    for bill in sorted(bills, key=lambda b: b.id):
        sponsor_name = "Unknown"
        if bill.sponsor_id is not None:
            sponsor = legislator_by_id.get(bill.sponsor_id)
            sponsor_name = sponsor.name if sponsor else "Unknown"

        summary.append(
            {
                "id": bill.id,
                "title": bill.title,
                "supporter_count": len(supporters.get(bill.id, set())),
                "opposer_count": len(opposers.get(bill.id, set())),
                "primary_sponsor": sponsor_name,
            }
        )
    return summary


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, object]]) -> None:
    """Write rows to CSV with provided field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def require_exists(path: Path) -> None:
    if not path.exists():
        console.print(f"Missing required file: {path}", style="red")
        raise typer.Exit(code=1)


def normalize_category(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value_lower = value.lower()
    if value_lower in DATASETS:
        return value_lower
    if value_lower in COMPUTED_PREVIEWS:
        return value_lower
    return None


def load_legislator_lookup(data_dir: Path) -> Dict[int, str]:
    legislators_path = data_dir / DATASETS["legislators"]
    require_exists(legislators_path)
    return {leg.id: leg.name for leg in load_legislators(legislators_path)}


def load_bill_lookup(data_dir: Path) -> Dict[int, Bill]:
    bills_path = data_dir / DATASETS["bills"]
    require_exists(bills_path)
    return {bill.id: bill for bill in load_bills(bills_path)}


def load_vote_lookup(data_dir: Path) -> Dict[int, Vote]:
    votes_path = data_dir / DATASETS["votes"]
    require_exists(votes_path)
    return load_votes(votes_path)


def enrich_rows(
    rows: List[Dict[str, str]], category: str, data_dir: Path
) -> tuple[List[Dict[str, object]], List[str]]:
    """Add friendly names/titles for relational IDs."""
    if category == "bills":
        legislators = load_legislator_lookup(data_dir)
        extra_fields = ["sponsor_name"]

        def enrich(row: Dict[str, str]) -> Dict[str, object]:
            sponsor_id = parse_int(
                row.get("Primary Sponsor")
                or row.get("primary_sponsor")
                or row.get("sponsor_id")
            )
            sponsor_name = legislators.get(sponsor_id, "Unknown") if sponsor_id else "Unknown"
            new_row = dict(row)
            new_row["sponsor_name"] = sponsor_name
            return new_row

        return [enrich(r) for r in rows], extra_fields

    if category == "votes":
        bills = load_bill_lookup(data_dir)
        extra_fields = ["bill_title"]

        def enrich(row: Dict[str, str]) -> Dict[str, object]:
            bill_id = parse_int(row.get("bill_id"))
            bill_title = bills.get(bill_id).title if bill_id in bills else "Unknown"
            new_row = dict(row)
            new_row["bill_title"] = bill_title
            return new_row

        return [enrich(r) for r in rows], extra_fields

    if category == "vote_results":
        legislators = load_legislator_lookup(data_dir)
        bills = load_bill_lookup(data_dir)
        votes = load_vote_lookup(data_dir)
        extra_fields = ["legislator_name", "bill_id", "bill_title"]

        def enrich(row: Dict[str, str]) -> Dict[str, object]:
            legislator_id = parse_int(row.get("legislator_id"))
            vote_id = parse_int(row.get("vote_id"))
            vote = votes.get(vote_id)
            bill_id = vote.bill_id if vote else None

            new_row = dict(row)
            new_row["legislator_name"] = legislators.get(legislator_id, "Unknown")
            new_row["bill_id"] = bill_id if bill_id is not None else ""
            if bill_id in bills:
                new_row["bill_title"] = bills[bill_id].title
            else:
                new_row["bill_title"] = "Unknown"
            return new_row

        return [enrich(r) for r in rows], extra_fields

    return rows, []


def format_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def select_category() -> Optional[str]:
    """Prompt user to choose which dataset to preview."""
    return questionary.select(
        "Pick a dataset to preview:",
        choices=[
            questionary.Choice("Bills (bills.csv)", value="bills"),
            questionary.Choice("Legislators (legislators.csv)", value="legislators"),
            questionary.Choice("Votes (votes.csv)", value="votes"),
            questionary.Choice(
                "Vote Results (vote_results.csv)", value="vote_results"
            ),
            questionary.Choice(
                COMPUTED_PREVIEWS["legislator_summary"], value="legislator_summary"
            ),
            questionary.Choice(
                COMPUTED_PREVIEWS["bill_summary"], value="bill_summary"
            ),
        ],
    ).ask()


def preview_dataset(data_dir: Path, category: str, limit: int = 30) -> None:
    if category in DATASETS:
        data_path = data_dir / DATASETS[category]
        require_exists(data_path)

        rows = list(itertools.islice(read_csv(data_path), limit))
        if not rows:
            console.print(f"No rows found in {data_path.name}.", style="yellow")
            return

        base_fieldnames = list(rows[0].keys())
        rows, extra_fields = enrich_rows(rows, category, data_dir)
        fieldnames = base_fieldnames + [
            f for f in extra_fields if f not in base_fieldnames
        ]
        title = f"First {len(rows)} rows from {data_path.name}"
    elif category == "legislator_summary":
        legislators_path = data_dir / DATASETS["legislators"]
        votes_path = data_dir / DATASETS["votes"]
        vote_results_path = data_dir / DATASETS["vote_results"]
        for path in [legislators_path, votes_path, vote_results_path]:
            require_exists(path)

        legislators = load_legislators(legislators_path)
        vote_results = load_vote_results(vote_results_path)
        votes = load_votes(votes_path)
        rows = compute_legislator_summary(legislators, vote_results, votes)[:limit]
        fieldnames = ["id", "name", "num_supported_bills", "num_opposed_bills"]
        title = f"{COMPUTED_PREVIEWS[category]} (first {len(rows)} rows)"
    elif category == "bill_summary":
        legislators_path = data_dir / DATASETS["legislators"]
        bills_path = data_dir / DATASETS["bills"]
        votes_path = data_dir / DATASETS["votes"]
        vote_results_path = data_dir / DATASETS["vote_results"]
        for path in [legislators_path, bills_path, votes_path, vote_results_path]:
            require_exists(path)

        legislators = load_legislators(legislators_path)
        bills = load_bills(bills_path)
        vote_results = load_vote_results(vote_results_path)
        votes = load_votes(votes_path)
        rows = compute_bill_summary(bills, legislators, vote_results, votes)[:limit]
        fieldnames = [
            "id",
            "title",
            "supporter_count",
            "opposer_count",
            "primary_sponsor",
        ]
        title = f"{COMPUTED_PREVIEWS[category]} (first {len(rows)} rows)"
    else:
        console.print(f"Unknown category: {category}", style="red")
        raise typer.Exit(code=1)

    table = Table(
        title=title,
        show_lines=True,
        header_style="bold cyan",
    )
    for field in fieldnames:
        table.add_column(field, overflow="fold")

    for row in rows:
        table.add_row(*(format_cell(row.get(field)) for field in fieldnames))

    console.print(table)


@app.command()
def summarize(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR,
        help=f"Directory containing bills.csv, legislators.csv, votes.csv, and vote_results.csv. (default: {DEFAULT_DATA_DIR})",
    ),
    legislator_output: Path = typer.Option(
        LEGISLATOR_OUTPUT,
        help=f"Output path for legislator summary CSV (default: {LEGISLATOR_OUTPUT}).",
    ),
    bill_output: Path = typer.Option(
        BILL_OUTPUT,
        help=f"Output path for bill summary CSV (default: {BILL_OUTPUT}).",
    ),
) -> None:
    """Compute legislator and bill vote summaries."""
    data_dir = data_dir.resolve()

    bills_path = data_dir / DATASETS["bills"]
    legislators_path = data_dir / DATASETS["legislators"]
    votes_path = data_dir / DATASETS["votes"]
    vote_results_path = data_dir / DATASETS["vote_results"]

    for path in [bills_path, legislators_path, votes_path, vote_results_path]:
        require_exists(path)

    legislators = load_legislators(legislators_path)
    bills = load_bills(bills_path)
    votes = load_votes(votes_path)
    vote_results = load_vote_results(vote_results_path)

    legislator_rows = compute_legislator_summary(legislators, vote_results, votes)
    bill_rows = compute_bill_summary(bills, legislators, vote_results, votes)

    write_csv(
        legislator_output,
        ["id", "name", "num_supported_bills", "num_opposed_bills"],
        legislator_rows,
    )
    write_csv(
        bill_output,
        ["id", "title", "supporter_count", "opposer_count", "primary_sponsor"],
        bill_rows,
    )

    console.print(
        f"Wrote {len(legislator_rows)} legislator rows -> {legislator_output}",
        style="green",
    )
    console.print(
        f"Wrote {len(bill_rows)} bill rows -> {bill_output}", style="green"
    )


@app.command()
def preview(
    data_dir: Path = typer.Option(
        DEFAULT_DATA_DIR, help=f"Directory containing the input CSV files. (default: {DEFAULT_DATA_DIR})"
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Dataset to preview (bills, legislators, votes, vote_results, legislator_summary, bill_summary).",
    ),
    limit: int = typer.Option(
        30,
        help="Number of rows to display from the chosen file.",
        min=1,
        max=1000,
    ),
) -> None:
    """Interactively preview the first rows of any input CSV."""
    data_dir = data_dir.resolve()
    normalized = normalize_category(category)
    if normalized is None:
        normalized = select_category()
        if normalized is None:
            console.print("No category selected, exiting.", style="yellow")
            raise typer.Exit(code=1)

    preview_dataset(data_dir, normalized, limit)


if __name__ == "__main__":
    app()
