from string import Template
from typing import List, Tuple

import orjson
from tinydb import Query, TinyDB

from mark.storage import FasterJSONStorage, YAMLStorage


class DataBase:
    def __init__(self, filename: str, storage="json"):
        if storage == "yaml":
            self.db = TinyDB(filename, indent=4, storage=YAMLStorage)
        else:
            self.db = TinyDB(
                filename, option=orjson.OPT_INDENT_2, storage=FasterJSONStorage
            )

    def insert_bookmark(self, table: str, bookmark_title: str, url: str):
        handle = self.db.table(table)
        handle.insert({"title": bookmark_title, "url": url})

    def insert_multiple(self, table: str, bookmark: List):
        handle = self.db.table(table)
        handle.insert_multiple(bookmark)

    def is_dir(self, table: str) -> bool:
        return table in self.db.tables()

    def get_bookmark(self, table: str, title: str) -> Tuple[str, str]:
        # TODO: handle title bein in path
        handle = self.db.table(table)
        return title, handle.search(Query().title == title)[0]["url"]

    def list_bookmarks(self, table: str, template: Template) -> List:
        # cache size is unlimited
        handle = self.db.table(table, cache_size=30)
        all_rows = handle.all()
        mapping = {
            template.safe_substitute(title=row.get("title")): row.get("title")
            for row in all_rows
        }
        return mapping

    def list_dirs(self, template: Template) -> List:
        return {
            template.safe_substitute(title=table): table for table in self.db.tables()
        }

    def get_table_handle(self, table_name: str):
        return self.db.table(table_name)


def save_bookmarks_to_db(bookmarks, db_file):
    db = DataBase(db_file)
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

    db = DataBase(db_file, trailing_char="")
    folders = db.list_dirs()
    for folder in folders:
        all_rows = db.get_table_handle(folder).all()
        write_folder(folder, all_rows)

    # force the data to os buffer
    file.flush()
    file.close()
