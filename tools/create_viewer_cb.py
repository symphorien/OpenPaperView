#!/usr/bin/env python3

import os.path
import time
import sqlite3
import re
import configparser
import warnings
import collections
# Fedora package : python3-PyPDF2
from PyPDF2 import PdfFileReader
from PyPDF2.utils import PdfReadError


class Document:
    def __init__(self, name):
        self.name = name
        self.title = None
        self.pdf_title = None
        self.thumb = None
        self.parts = []
        self.original_images = {}
        self.edited_images = {}
        self.image_sizes = {}
        self.labels = []
        self.date = 0
        self.mtime = 0
        self.page_count = 0
        self.size = 0
        self.text = ""
        self.extra_keywords = None
        self.original_extra = None
        self.index_level = 999


# documents by id
# the id being the directory name
# and documents.doc_id in paperwork's doc_tracking.db
documents = dict()
cleaner = re.compile(r"\W+")


def warn(code, message):
    if config.getboolean('warnings', code):
        print(message)


def scan_data_dir():
    # Add all documents
    print(f"Scanning {data_base_dir}")
    for d in os.scandir(data_base_dir):
        if d.is_dir():
            scan_doc_dir(d.path)
    print(f'Found {len(documents)} documents')


def scan_doc_dir(dir_path):
    # Add a document from the files in this directory

    doc_id = os.path.split(dir_path)[-1]
    doc = Document(doc_id)
    documents[doc_id] = doc

    # extract the datetime from the dir name
    date_str = re.fullmatch(r'(\d{8}_\d{4})(?:_.*)?', doc_id).group(1)
    date_tuple = time.strptime(date_str, '%Y%m%d_%H%M')
    date_epoch = time.mktime(date_tuple)
    date_ms = int(date_epoch * 1000)
    doc.date = date_ms

    thumbs = []

    for f in os.scandir(dir_path):
        if not f.is_file():
            continue

        stat = f.stat()
        name = os.fsdecode(f.name)
        if name == 'labels':
            # one label per line
            # only the label, not the color
            doc.labels = read_text(f.path).splitlines()
        elif name == 'extra.txt':
            # optional title (firstline beginning with #)
            # and extra keywords
            doc.original_extra = read_text(f.path)
            extras = doc.original_extra.splitlines()
            if extras and extras[0].startswith('#'):
                doc.title = extras[0].removeprefix('#').strip()
                extras = extras[1:]
            doc.extra_keywords = clean_text(" ".join(extras))
        elif name == 'doc.pdf':
            # PDF, try to count the pages
            doc.parts.append(name)
            doc.size = stat.st_size
            doc.page_count, doc.pdf_title = get_pdf_info(f.path)
        elif m := re.fullmatch(r'paper\.(\d+)\.jpg', name):
            # original image
            doc.original_images[m.group(1)] = name
            doc.image_sizes[name] = stat.st_size
        elif m := re.fullmatch(r'paper\.(\d+)\.edited\.jpg', name):
            # edited image
            doc.edited_images[m.group(1)] = name
            doc.image_sizes[name] = stat.st_size
        elif re.fullmatch(r'paper\.\d+\.thumb\.jpg', name):
            # thumbnail, only one ?
            thumbs.append(name)
        elif re.fullmatch(r'paper\.\d+\.words', name):
            pass
        else:
            warn('unknown_file_type', f'unknown file type in {dir_path}: "{name}"')

    if doc.parts:
        # PDF, ignore images
        if doc.original_images:
            # Does it happen ?
            warn("multiple_types", f"Error : both PDF and images for '{dir_path}' ???")
        elif doc.edited_images:
            warn("pdf_with_edited_images", f"Ignoring {len(doc.edited_images)} edited images for PDF '{dir_path}'")
    else:
        # Images, take the edited one
        doc.parts.extend((doc.original_images | doc.edited_images).values())
        doc.size = sum([doc.image_sizes[i] for i in doc.parts])
        doc.page_count = len(doc.parts)

    if thumbs:
        doc.thumb = sorted(thumbs)[0]

    if not doc.title:
        warn("missing_title", f"Missing title : '{dir_path}'")

    if not doc.parts:
        raise Exception("No parts ???")


def add_meta_data():
    print(f"Adding metadata from {doc_db}")
    con = sqlite3.connect(doc_db)

    cur = con.cursor()

    for (doc_id, doc_text, doc_mtime) in cur.execute('SELECT DOC_ID, TEXT, MTIME FROM DOCUMENTS ORDER BY MTIME'):
        doc = documents[doc_id]

        # remove the title from the extras
        # (which Paperwork added to the text)
        # but keep the other extra
        if doc.original_extra and doc_text.endswith(doc.original_extra):
            doc_text = doc_text.removesuffix(doc.original_extra) + " " + doc.extra_keywords

        doc.text = clean_text(doc_text)
        doc.mtime = doc_mtime * 1000

    con.close()


CONTENT_IGNORED = 1
CONTENT_DATA = 2
CONTENT_INDEX = 3
CONTENT_FULL = 4

LEVELS = {
    'ignored': CONTENT_IGNORED,
    'data': CONTENT_DATA,
    'index': CONTENT_INDEX,
    'full': CONTENT_FULL,
}


def define_index_level():
    """Set the index level of all documents, based on the config"""
    label_levels = collections.defaultdict(lambda: CONTENT_FULL)

    for label, level in config.items('labels'):
        if level not in LEVELS:
            raise Exception(f"The level '{level}' (for label '{label}') does not exist")
        label_levels[label] = LEVELS[level]

    for doc in documents.values():
        doc.index_level = min([label_levels[label.partition(',')[0]] for label in doc.labels], default=CONTENT_FULL)


def create_db():
    print(f"Saving in {result_db}")
    os.remove(result_db)
    con = sqlite3.connect(result_db)
    cur = con.cursor()

    cur.executescript('''
CREATE TABLE Document (
  documentId INTEGER NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  title TEXT NULL,
  thumb TEXT NULL,
  pageCount INTEGER NOT NULL,
  date INTEGER NOT NULL,
  mtime INTEGER NOT NULL,
  size INTEGER NOT NULL
);

CREATE TABLE Part (
  partId INTEGER NOT NULL PRIMARY KEY,
  documentId INTEGER NOT NULL,
  name TEXT NOT NULL,
  downloadStatus INTEGER NOT NULL DEFAULT 100,
  downloadError TEXT NULL,
  CONSTRAINT fkDocument FOREIGN KEY (documentId) REFERENCES Document(documentId)
);
CREATE INDEX Part_documentId on Part(documentId);
CREATE INDEX Part_downloadStatus on Part(downloadStatus);

CREATE TABLE Label (
  labelId INTEGER NOT NULL PRIMARY KEY,
  documentId INTEGER NOT NULL,
  name TEXT NOT NULL,
  color TEXT,
  CONSTRAINT fkDocument FOREIGN KEY (documentId) REFERENCES Document(documentId)
);
CREATE INDEX Label_documentId on Label(documentId);
CREATE INDEX Label_name on Label(name);

CREATE TABLE DocumentText (
  documentId INTEGER NOT NULL PRIMARY KEY,
  main TEXT NOT NULL,
  additional TEXT NULL,
  CONSTRAINT fkDocument FOREIGN KEY (documentId) REFERENCES Document(documentId)
);

CREATE VIRTUAL TABLE DocumentFts USING FTS4(
  tokenize=unicode61,
  content=`DocumentText`,
  main,
  additional
);

-- used by Room
PRAGMA user_version = 1;

''')

    # so that order by rowid == order by date desc
    sorted_docs = sorted(documents.values(), key=lambda doc: -doc.date)

    for idx, doc in enumerate(sorted_docs):
        # base data
        if doc.index_level >= CONTENT_DATA:
            cur.execute('''
INSERT INTO Document(documentId, name, title, thumb, pageCount, date, mtime, size)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (idx, doc.name, doc.title, doc.thumb, doc.page_count, doc.date, doc.mtime, doc.size))

            for part in doc.parts:
                cur.execute("""
        INSERT INTO Part(documentId, name) VALUES (?, ?)
        """, (idx, part))

            for label in doc.labels:
                label_name, label_color = label.split(',', 1)
                cur.execute("""
        INSERT INTO Label(documentId, name, color) VALUES (?, ?, ?)
        """, (idx, label_name, label_color))

        # The FTS index
        if doc.index_level >= CONTENT_INDEX:
            cur.execute("""
INSERT INTO DocumentFts(rowid, main, additional) VALUES (?, ?, ?)
""", (idx, doc.text, doc.title if doc.title else doc.pdf_title))

        # Full text content
        if doc.index_level >= CONTENT_FULL:
            cur.execute("""
        INSERT INTO DocumentText(rowid, main, additional) VALUES (?, ?, ?)
""", (idx, doc.text, doc.title))

    # rebuild FTS tree
    # see https://www.sqlite.org/fts3.html
    con.execute("INSERT INTO DocumentFts(DocumentFts) VALUES('optimize')")
    con.commit()
    # not sure why (no rows were deleted) but reduce the file by 25%
    con.execute("VACUUM")
    con.commit()
    # rebuild statistics
    con.execute("PRAGMA optimize")
    con.execute("ANALYZE")
    con.commit()
    con.close()


def get_pdf_info(path):
    # Count page number, 0 if error

    with open(path, 'rb') as f:
        try:
            pdf = PdfFileReader(f)
            title = None
            page_count = pdf.getNumPages()

            info = pdf.getDocumentInfo()
            if info:
                title = info.title
                if title in (None, '', 'Title', 'title'):
                    title = info.subject
                if title in (None, '', 'Subject', 'subject'):
                    title = None

            return page_count, title
        except (PdfReadError, ValueError) as ex:
            warn("pdf_error", f"Error '{path}' : {ex}")
            return 0, None


def read_text(path):
    # Read file as text

    with open(path) as file:
        return file.read()


def clean_text(txt):
    # Remove non character

    return cleaner.sub(" ", txt)


if __name__ == '__main__':

    for configDir in ['', '~/.config', os.path.dirname(os.path.abspath(__file__))]:
        configFile = os.path.join(os.path.expanduser(configDir), 'create_viewer_cb.config')
        if os.path.exists(configFile):
            break

    print(f"Reading config from '{configFile}'")
    config = configparser.ConfigParser()
    config.read(configFile)

    data_base_dir = os.path.expanduser(config['paths']['papers_data_dir'])
    doc_db = os.path.expanduser(config['paths']['papers_metadata_db'])
    result_db = os.path.expanduser(config['paths']['result_db'])

    # is there a way to filter only the annoying warnings of PyPDF2 ?
    if not config.getboolean("warnings", "pdf_error"):
        warnings.filterwarnings("ignore")

    scan_data_dir()
    add_meta_data()
    define_index_level()
    create_db()
