import json
import hashlib
import os
import gzip
import requests
import html.entities
# from lxml import etree as ET
import xml.etree.ElementTree as ET
from tqdm import tqdm

DBLP_URL = "https://dblp.org/xml/dblp.xml.gz"
MD5_URL = "https://dblp.org/xml/dblp.xml.gz.md5"
LOCAL_FILE = "dblp.xml.gz"
LOCAL_DIR = 'dblp_data'
ETAG_FILE = LOCAL_FILE + ".etag"
CHUNK_SIZE = 8192



class CustomEntity:
    def __getitem__(self, key):
        if key == 'umml':
            key = 'uuml' # Fix invalid entity
        return chr(html.entities.name2codepoint[key])


parser = ET.XMLParser()
parser.entity.update(html.entities.entitydefs)
parser.entity['umml'] = parser.entity['uuml']


def get_remote_md5():
    resp = requests.get(MD5_URL, timeout=30)
    resp.raise_for_status()
    return resp.text.strip().split()[0]


def download_file(url, dest_path, etag=None):
    md5 = hashlib.md5()
    headers = {}
    if etag:
        headers["If-None-Match"] = etag

    r = requests.get(url, headers=headers, stream=True, timeout=60)
    if r.status_code == 304:
        # Remote file unchanged (ETag match)
        return None, None
    r.raise_for_status()

    with open(dest_path, "wb") as f, tqdm(total=int(r.headers.get('Content-Length', 0)), unit='iB', unit_scale=True, desc='dblp.xml.gz') as pbar:
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                md5.update(chunk)
                pbar.update(len(chunk))

    new_etag = r.headers.get("ETag")
    return new_etag, md5.hexdigest()


def get_local_etag():
    if os.path.exists(f'{LOCAL_DIR}/{ETAG_FILE}'):
        with open(f'{LOCAL_DIR}/{ETAG_FILE}', "r") as f:
            return f.read().strip()
    return None


def get_dblp_file():
    local_etag = get_local_etag()
    tmp_file = LOCAL_FILE + ".tmp"

    new_etag, new_md5 = download_file(DBLP_URL, tmp_file, etag=local_etag)

    if new_etag is None:
        print("dblp.xml.gz already up-to-date.")
        return f'{LOCAL_DIR}/{LOCAL_FILE}'
    else:
        remote_md5 = get_remote_md5()
        if new_md5.strip().lower() == remote_md5.strip().lower():
            if not os.path.exists(LOCAL_DIR):
                os.makedirs(LOCAL_DIR, exist_ok=True)
            else:
                for f in os.listdir(LOCAL_DIR):
                    os.remove(os.path.join(LOCAL_DIR, f))
            os.replace(tmp_file, f'{LOCAL_DIR}/{LOCAL_FILE}')
            with open(f'{LOCAL_DIR}/{LOCAL_FILE}', "w") as f:
                f.write(new_etag)
        else:
            os.remove(tmp_file)
            raise ValueError("MD5 checksum mismatch — download aborted!")

    return f'{LOCAL_DIR}/{LOCAL_FILE}'


def cache_author_pub_mappings():
    authors = {}
    publications = {}

    # iterparse returns events and elements as they are read
    with gzip.open(get_dblp_file(), 'rb') as f:
        context = ET.iterparse(f, events=('end',), parser=parser)
        _, root = next(context)  # get root element <dblp>

        for event, elem in tqdm(context, desc="extracting author/pub mappings from dblp.xml.gz", unit='elem'):
            tag = elem.tag

            if tag in {"article", "inproceedings", "proceedings", "book",
                         "incollection", "phdthesis", "mastersthesis",
                         "www", "data"}:
                pub_key = elem.attrib.get("key")
                if pub_key:
                    author_names = [a.text for a in elem.findall("author") if a.text]
                    publications[pub_key] = author_names
                    for author_name in author_names:
                        if author_name not in authors:
                            authors[author_name] = []
                        authors[author_name].append(pub_key)

                elem.clear()
                root.clear()

    print('writing author2pubs cache')
    with gzip.open(f'{LOCAL_DIR}/author2pubs.json.gz', 'w') as f:
        json.dump(authors, f)

    print('writing pub2authors cache')
    with gzip,open(f'{LOCAL_DIR}/pub2authors.json.gz', 'w') as f:
        json.dump(publications, f)


def get_pub2authors():
    if not os.path.exists(f'{LOCAL_DIR}/pub2authors.json.gz'):
        cache_author_pub_mappings()

    with gzip.open(f'{LOCAL_DIR}/pub2authors.json.gz', 'r') as f:
        pub2authors = json.load(f)

    return pub2authors


def get_author2pubs():
    if not os.path.exists(f'{LOCAL_DIR}/author2pubs.json.gz'):
        cache_author_pub_mappings()

    with gzip.open(f'{LOCAL_DIR}/author2pub.json.gz', 'r') as f:
        author2pub = json.load(f)

    return author2pub


def get_author2id():
    author2pub = get_author2pubs()
    author2id = {}
    for author, pubs in author2pub.items():
        author_homepages = [x for x in pubs if x.startswith('homepages/')]
        if author_homepages:
            author_id = author_homepages[0][len('homepages/'):]
            author2id[author] = author_id
    return author2id


def main():
    author2id = get_author2id()
    import pdb; pdb.set_trace()
    author2id


if __name__ == "__main__":
    main()
