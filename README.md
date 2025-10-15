# dblp-conf-tools

This is an ad hoc set of tools for working using dblp to help in conference chairing duties with EasyChair.

## Installation and Setup

Requires Python. (I've used this code with Python 3.13, but it should probably work on other versions too.)

Clone and install dependencies:

```
git clone https://github.com/seanmacavaney/dblp-conf-tools.git
cd dblp-conf-tools
pip install -r requirements.txt
```

## Matching Authors/Reviewers to DBLP

You can match authors and reviewers to their DBLP name using `match_dblp.py`. The script augments EasyChair author/committee CSV
files with `dblp_[id,name,affiliations]` columns that are matched to the reviewer. It uses the DBLP XML file for exact matching,
and falls back on the search API when matches are ambiguous.

You first need to download the author/committee CSV listing from EasyChair. This is accessible under:
`Conference >> Conference data download >> CSV (click here)`. Tick "Program committee" and/or "Authors" and download.

Once you have the CSV file, run the script:

```
python match_dblp.py author.csv # or committee.csv
```

The script will show progress as it's matching. Some cases are ambiguous, and the script will show possible choices
in this setting. These choices can be entered into the final spreadsheet manually, or provided as interactive input
to the script when the `-interactive` flag is provided.

In general, we'd expect all committee members to be matched to a DBLP record, since they should be established researchers
in the field. In contrast, not all authors will have DBLP records, since some may be students or from industry. It's okay
to leave these ones blank.

Finally, note that the matching process is not perfect due to challenges inherent to the authorship matching. It's a good idea
to review the resulting file for anomalies and cross-reference with other sources when possible.

## Identify Conflicts from Recent Co-Authorship

The `find_conflicts.py` script takes in the author/committee CSV files that are augmented with DBLP information and
identifies conflicts of interest based on recent co-authored papers.

```
python find_conflicts.py committee.csv author.csv
```

It outputs the conflicts to stdout. We're still finding a way to import these conflicts into EasyChair.
