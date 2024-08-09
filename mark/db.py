import html
from string import Template
from typing import List, Tuple

import orjson
from tinydb import Query, TinyDB

from mark.storage import FasterJSONStorage, YAMLStorage
from mark.utils import are_urls_equal


class DataBase:
    def __init__(self, filename: str, storage="json"):
        if storage == "yaml":
            self.db = TinyDB(filename, indent=4, storage=YAMLStorage)
        else:
            self.db = TinyDB(
                filename, option=orjson.OPT_INDENT_2, storage=FasterJSONStorage
            )

    def insert_bookmark(self, table: str, url: str, title: str):
        handle = self.db.table(table)
        handle.insert({"title": title, "url": url})

    def insert_multiple(self, table: str, bookmark: List):
        handle = self.db.table(table)
        handle.insert_multiple(bookmark)

    def is_dir(self, table: str) -> bool:
        return table in self.db.tables()

    def get_bookmark(self, tablename: str, title: str) -> Tuple[str, str]:
        # TODO: handle title bein in path
        handle = self.db.table(tablename)
        return title, handle.search(Query().title == title)[0]["url"]

    def bookmark_exists_in_table(self, tablename, url):
        handle = self.db.table(tablename)
        query = handle.search(Query().url.test(are_urls_equal, url))
        return len(query) > 0

    def list_bookmarks(
        self, tablename: str, template: Template = Template("$title")
    ) -> List:
        # cache size is unlimited
        handle = self.db.table(tablename, cache_size=30)
        all_rows = handle.all()
        mapping = {
            template.safe_substitute(title=html.escape(row.get("title"))): row.get(
                "title"
            )
            for row in all_rows
        }
        return mapping

    def list_dirs(self, template: Template = Template("$title")) -> List:
        return {
            template.safe_substitute(title=html.escape(table)): table
            for table in self.db.tables()
        }

    def get_table_handle(self, tablename: str):
        return self.db.table(tablename)


def prune_duplicates(db, bookmarks):
    """
    if the url is already there under table then ignore this bookmark
    """
    for table in bookmarks:
        # skip un-necessary calls if the table is not in the db
        if not db.is_dir(table):
            continue
        folder = []
        n = len(bookmarks[table])
        for i in range(n):
            bookmark = bookmarks[table][i]
            if not db.bookmark_exists_in_table(table, bookmark["url"]):
                folder.append(bookmark)
        # update folder list
        bookmarks[table] = folder
    return bookmarks


def save_bookmarks_to_db(bookmarks, db_file, no_duplicates):
    db = DataBase(db_file)
    if no_duplicates:
        bookmarks = prune_duplicates(db, bookmarks)
    # do the insertion
    for table in bookmarks:
        db.insert_multiple(table, bookmarks[table])


def export_bookmarks_to_markdown(db_file: str, filepath: str, heading: int):

    assert 1 <= heading <= 6
    # use append option "a" to avoid removing current content of the file
    file = open(filepath, "a+")
    heading_level = "#" * heading

    def write_folder(folder_name, rows):
        folder_header = f"\n\n\n{heading_level} {folder_name}\n\n\n"
        file.write(folder_header)
        for row in rows:
            title = row.get("title")
            url = row.get("url")
            line = f"[{title}]({url})\n\n"
            file.write(line)

    db = DataBase(db_file)
    folders = db.list_dirs()
    for folder in folders:
        all_rows = db.get_table_handle(folder).all()
        write_folder(folder, all_rows)

    # force the data to os buffer
    file.flush()
    file.close()
