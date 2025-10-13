import hashlib
import os
import gzip
import requests
import html.entities
from collections import Counter
# from lxml import etree as ET
import xml.etree.ElementTree as ET
from tqdm import tqdm

DBLP_URL = "https://dblp.org/xml/dblp.xml.gz"
MD5_URL = "https://dblp.org/xml/dblp.xml.gz.md5"
LOCAL_FILE = "dblp.xml.gz"
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
    if os.path.exists(ETAG_FILE):
        with open(ETAG_FILE, "r") as f:
            return f.read().strip()
    return None


def get_dblp_file():
    local_etag = get_local_etag()
    tmp_file = LOCAL_FILE + ".tmp"

    new_etag, new_md5 = download_file(DBLP_URL, tmp_file, etag=local_etag)

    if new_etag is None:
        print("dblp.xml.gz already up-to-date.")
        return LOCAL_FILE
    else:
        remote_md5 = get_remote_md5()
        if new_md5.strip().lower() == remote_md5.strip().lower():
            os.replace(tmp_file, LOCAL_FILE)
            with open(ETAG_FILE, "w") as f:
                f.write(new_etag)
        else:
            os.remove(tmp_file)
            raise ValueError("MD5 checksum mismatch — download aborted!")

    return LOCAL_FILE


def get_authors_and_pubs(local_file=LOCAL_FILE):
    authors = []
    publications = {}
    c = Counter()

    # iterparse returns events and elements as they are read
    with gzip.open(local_file, 'rb') as f:
        context = ET.iterparse(f, events=('end',), parser=parser)
        _, root = next(context)  # get root element <dblp>

        for event, elem in tqdm(context, desc="parsing dblp.xml.gz", unit='elem'):
            tag = elem.tag
            c[tag] += 1

            # --- PERSON entries ---
            if tag == "person":
                person_key = elem.attrib.get("key")
                names = [a.text for a in elem.findall("author") if a.text]
                urls = [u.text for u in elem.findall("url") if u.text]
                notes = [n.text for n in elem.findall("note") if n.text]
                pubs = [c.text for c in elem.findall("cite") if c.text and c.text != "..."]

                authors.append({
                    "key": person_key,
                    "names": names,
                    "urls": urls,
                    "notes": notes,
                    "publications": pubs,
                })

                # clear to free memory
                elem.clear()
                root.clear()

            # # --- PUBLICATION entries ---
            # elif tag in {"article", "inproceedings", "proceedings", "book",
            #              "incollection", "phdthesis", "mastersthesis",
            #              "www", "data"}:
            #     pub_key = elem.attrib.get("key")
            #     if pub_key:
            #         author_names = [a.text for a in elem.findall("author") if a.text]
            #         publications[pub_key] = author_names

            #     elem.clear()
            #     root.clear()
        print(c)

        return authors, publications


def main():
    # get_dblp_file()
    authors, pubs = get_authors_and_pubs()
    # import pdb; pdb.set_trace()
    authors, pubs


if __name__ == "__main__":
    main()
