# Writeup

## 1. Time complexity and tradeoffs
My program goes through each file once, builds some dictionaries in memory, and then sorts the final results.
The running time grows more or less linearly with the total number of rows in the CSVs, plus a small extra cost for sorting at the end.
I keep all data (legislators, bills, votes, vote results) in memory to make the code simpler and the lookups fast.
I use sets to track which bills were supported or opposed so I don’t double-count.
This uses a bit more memory, but makes the counts correct and keeps the code easy to follow.

## 2. Future columns (e.g., “Bill Voted On Date”, “Co-Sponsors”)
I would not change the main logic that loops over the data.
This part should be easy to achieve by just adding one new collumn in row builder

## 3. If given a list of legislators or bills to generate a CSV for
If I receive Python lists instead of CSV files, I would:
Skip the CSV loading step.
Take those lists (legislators, bills, votes, vote_results) as function inputs.
Run the same summary logic and then write the CSV output as before.
If I only need a subset (e.g. only some legislator IDs or bill IDs), I would just filter the lists first and then reuse the same code.

## 4. Time spent
- Roughly 1.5 hours total, including the CLI/preview additions and documentation updates.
