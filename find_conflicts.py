from collections import defaultdict
import csv
from dblp_data import get_author2id, get_author2pubs, get_pub2authors


def main(committee_csv, author_csv):    
    author2id = get_author2id()

    id2pubs = {}
    for author, pubs in get_author2pubs().items():
        if author in author2id:
            if author2id[author] not in id2pubs:
                id2pubs[author2id[author]] = set()
            id2pubs[author2id[author]].update(pubs)

    pub2ids = {}
    for pub, authors in get_pub2authors().items():
        pub2ids[pub] = set()
        for author in authors:
            if author in author2id:
                pub2ids[pub].add(author2id[author])

    # find conflicts as authors who have publications with a member of the committee
    committee_ids = {}
    person_num_mapping = {}
    with open(committee_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row.get('dblp_id'):
                committee_ids[row['dblp_id']] = row['person #']
            person_num_mapping[row['person #']] = row['first name'] + ' ' + row['last name']

    cois = defaultdict(list)
    author_ids = {}
    with open(author_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Only update if conflicts is missing or empty
            dblp = row.get('dblp_id')
            if dblp:
                author_ids[dblp] = row['person #']
            author_name = row['first name'] + ' ' + row['last name']
            if dblp in id2pubs:
                for pub in id2pubs[dblp]:
                    for conflict in pub2ids[pub] & committee_ids.keys():
                        cois[(row['submission #'], conflict)].append(f'{pub} with {author_name}')

    with open('conflicts.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['Member #', 'Member Name', 'submission #', 'conflict_details'])
        writer.writeheader()
        for submission_num, committee_dblp in sorted(cois):
            committee_num = committee_ids[committee_dblp]
            committee_name = person_num_mapping[committee_num]
            writer.writerow({
                'Member #': committee_num,
                'Member Name': committee_name,
                'submission #': submission_num,
                'conflict_details': '; '.join(cois[submission_num, committee_dblp])
            })


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Update CSV with DBLP IDs.")
    parser.add_argument("committee_csv")
    parser.add_argument("author_csv")
    args = parser.parse_args()
    main(args.committee_csv, args.author_csv)
