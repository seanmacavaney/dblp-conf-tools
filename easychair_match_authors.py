import re
import csv
from dblp_data import get_author2id
from pyterrier_services import DblpApi

dblp = DblpApi()


def update_csv_with_dblp(input_file, output_file, *, interactive=False):
    author2id = get_author2id()

    # Read the CSV
    with open(input_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames if reader.fieldnames else []

        # Add 'dblp' column if it doesn't exist
        if 'dblp' not in fieldnames:
            fieldnames.append('dblp')

        rows = []
        for row in reader:
            # Only update if dblp is missing or empty
            if not row.get('dblp'):
                name = (row.get('first name', '') + ' ' + row.get('last name', '')).strip()
                if name in author2id:
                    row['dblp'] = author2id[name]
                else:
                    matches = dblp.search(name, entity_type='author')
                    # matcher = re.compile(r'^' + re.escape(name) + r'( )\d+$', re.IGNORECASE)
                    # matches = [aid for aname, aid in author2id.items() if matcher.match(aname)]
                    if len(matches) == 1:
                        row['dblp'] = matches.iloc[0]['docno']
                    elif len(matches) > 1:
                        print(f'{name} - {row.get('affiliation')} {row.get('country')}')
                        for i, record in enumerate(matches.itertuples()):
                            print(f'  {i} {record.docno}: {record.author} - {', '.join(record.affiliations)} https://dblp.org/pid/{record.docno}.html')
                        if interactive:
                            selected = input("Enter the dblp ID to use, index of the dblp ID, or leave blank to skip: ").strip()
                            if selected:
                                if '/' in selected:
                                    row['dblp'] = selected
                                else:
                                    try:
                                        row['dblp'] = matches.iloc[int(selected)]['docno']
                                    except ValueError:
                                        pass
                        print()
                    else:
                        print(f'{name} - {row.get('affiliation')} {row.get('country')}')
                        print('  [no matches found]')
                        print()
            rows.append(row)

    # Write the updated CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Update CSV with DBLP IDs.")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("--output_csv", help="Path to save updated CSV file")
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()
    if args.output_csv is None:
        args.output_csv = args.input_csv
    
    update_csv_with_dblp(args.input_csv, args.output_csv, interactive=args.interactive)
    print(f"Updated CSV saved to {args.output_csv}")
