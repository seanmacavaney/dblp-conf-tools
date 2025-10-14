import re
import csv
from urllib.parse import quote
from dblp_data import get_author2id, get_disambiguation2id, get_author2pubs
from pyterrier_services import DblpApi
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('match_dblp')

dblp = DblpApi()
dblp_author_retr = dblp.retriever(num_results=30, entity_type='author', verbose=False)

pub_re = re.compile('conf/(sigir|ecir)')

author2pubs = get_author2pubs()

def update_csv_with_dblp(input_file, output_file, *, interactive=False):
    author2id = get_author2id()
    disambiguation2id = get_disambiguation2id()

    # Read the CSV
    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames if reader.fieldnames else []

        # Add 'dblp' columns if they don't exist
        if 'dblp_id' not in fieldnames:
            fieldnames.append('dblp_id')
        if 'dblp_name' not in fieldnames:
            fieldnames.append('dblp_name')
        if 'dblp_affiliations' not in fieldnames:
            fieldnames.append('dblp_affiliations')

        rows = []
        for row in reader:
            # Only update if dblp is missing or empty
            if not row.get('dblp_id'):
                name = (row.get('first name', '') + ' ' + row.get('last name', '')).strip()
                if name in author2id:
                    logger.info(f'Matched {name} -> {author2id[name]} using exact match')
                    row['dblp_id'] = author2id[name]
                    row['dblp_name'] = name
                    row['dblp_affiliations'] = ''
                else:
                    matches = None
                    if name in disambiguation2id:
                        logger.info(f'{name} matches disambiguation page (downloading)')
                        try:
                            matches = dblp.load_disambiguation(disambiguation2id[name])
                        except Exception as e:
                            logger.error(f'Error loading disambiguation for {name}: {e}')
                            matches = None
                    if matches is not None and len(matches) > 0:
                        choose_dblp_from_candidates(row, name, matches, interactive=interactive)
                    else:
                        logger.info(f'perfomring api search for {name}')
                        try:
                            matches = dblp_author_retr.search(name)
                        except Exception as e:
                            logger.error(f'Error searching for {name}: {e}')
                            matches = None
                        choose_dblp_from_candidates(row, name, matches, interactive=interactive)
            if row.get('dblp_id') and (not row.get('dblp_name') or not row.get('dblp_affiliations')):
                logger.info(f'Loading author record for {name} ' + row['dblp_id'])
                try:
                    record = dblp.load_author(row['dblp_id'])
                except Exception as e:
                    logger.error(f'Error loading author record for {row["dblp_id"]}: {e}')
                    record = None
                if record:
                    if not row.get('dblp_name'):
                        row['dblp_name'] = record['name']
                    if not row.get('dblp_affiliations'):
                        row['dblp_affiliations'] = '; '.join(record.get('affiliations', [])) or '[None Listed]'
            rows.append(row)

    # Write the updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def choose_dblp_from_candidates(row, name, matches, *, interactive=False):
    if matches is None:
        return
    elif len(matches) == 0:
        print(f'{name} - {row.get('affiliation')} {row.get('country')}')
        print('  [no matches found]')
        print()
    elif len(matches) == 1:
        logger.info(f'Matched {name} -> {matches.iloc[0]["docno"]} based on single result')
        row['dblp_id'] = matches.iloc[0]['docno']
        row['dblp_name'] = matches.iloc[0]['author']
        row['dblp_affiliations'] = '; '.join(matches.iloc[0]['affiliations']) or '[None Listed]'
    else:
        affiliation_matches = matches[matches['affiliations'].apply(lambda affs: any(row.get('affiliation', '').lower() in (a.lower() if a else '') for a in affs))]
        if len(affiliation_matches) == 1:
            logger.info(f'Matched {name} -> {affiliation_matches.iloc[0]["docno"]} based on single affiliation match')
            row['dblp_id'] = affiliation_matches.iloc[0]['docno']
            row['dblp_name'] = affiliation_matches.iloc[0]['author']
            row['dblp_affiliations'] = '; '.join(affiliation_matches.iloc[0]['affiliations']) or '[None Listed]'
        elif len(matches) > 1:
            print(f'{name} - {row.get('affiliation')} {row.get('country')}')
            print(f'https://dblp.org/search?q={quote(name)}')
            for i, record in enumerate(matches.itertuples()):
                pubs = author2pubs.get(record.author, [])
                pubs = [p for p in pubs if pub_re.search(p)][:5]
                pubs = ', '.join(pubs)
                print(f'  {i} {record.docno}: {record.author} - {', '.join(record.affiliations)} https://dblp.org/pid/{record.docno}.html {pubs}')
            if interactive:
                selected = input("Enter the dblp ID to use, index of the dblp ID, or leave blank to skip: ").strip()
                if selected:
                    if '/' in selected:
                        row['dblp_id'] = selected
                        record = matches[matches['docno'] == selected]
                        if not record.empty:
                            row['dblp_name'] = record.iloc[0]['author']
                            row['dblp_affiliations'] = '; '.join(record.iloc[0]['affiliations']) or '[None Listed]'
                        else:
                            row['dblp_name'] = ''
                            row['dblp_affiliations'] = ''
                    else:
                        try:
                            record = matches.iloc[int(selected)]
                        except (IndexError, ValueError):
                            print("Invalid selection, skipping.")
                        row['dblp_id'] = record['docno']
                        row['dblp_name'] = record['author']
                        row['dblp_affiliations'] = '; '.join(record['affiliations']) or '[None Listed]'
            print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Update CSV with DBLP information.")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("--output_csv", help="Path to save updated CSV file (defaults to input_csv if not provided)")
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()
    if args.output_csv is None:
        args.output_csv = args.input_csv
    
    update_csv_with_dblp(args.input_csv, args.output_csv, interactive=args.interactive)
    print(f"Updated CSV saved to {args.output_csv}")
