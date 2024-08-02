from typing import List, Tuple

import orjson
from tinydb import Query, TinyDB

from mark.storage import FasterJSONStorage, YAMLStorage


class DataBase:
    def __init__(self, filename: str, trailing_char: str = "\\", storage="json"):
        assert len(trailing_char) <= 1
        if storage == "yaml":
            self.db = TinyDB(filename, indent=4, storage=YAMLStorage)
        else:
            self.db = TinyDB(
                filename, option=orjson.OPT_INDENT_2, storage=FasterJSONStorage
            )
        self.trailing_char = trailing_char

    def insert_bookmark(self, table: str, bookmark_title: str, url: str):
        table = self.__handle_path(table)
        handle = self.db.table(table)
        handle.insert({"title": bookmark_title, "url": url})

    def insert_multiple(self, table: str, bookmark: List):
        handle = self.db.table(table)
        handle.insert_multiple(bookmark)

    def is_dir(self, table: str) -> bool:
        table = self.__handle_path(table)
        return table in self.db.tables()

    def __handle_path(self, table: str) -> str:
        if table.endswith(self.trailing_char):
            table = table.rstrip(self.trailing_char)
        return table

    def get_bookmark(self, table: str, title: str) -> Tuple[str, str]:
        table = self.__handle_path(table)
        # TODO: handle title bein in path
        handle = self.db.table(table)
        return title, handle.search(Query().title == title)[0]["url"]

    def list_bookmarks(self, table: str, is_full: bool = False) -> List:
        table = self.__handle_path(table)
        # cache size is unlimited
        handle = self.db.table(table, cache_size=30)
        all_rows = handle.all()
        parent = f"{table}{self.trailing_char}" if is_full else ""
        attrs = ["%s%s" % (parent, row.get("title")) for row in all_rows]
        return attrs

    def list_dirs(self) -> List:
        return [f"{table}{self.trailing_char}" for table in self.db.tables()]

    def get_table_handle(self, table_name: str):
        return self.db.table(table_name)


def save_bookmarks_to_db(bookmarks, db_file):
    db = DataBase(db_file)
    for table in bookmarks:
        db.insert_multiple(table, bookmarks[table])


def convert_bookmarks_to_markdown(db_file: str, filepath: str, heading: int):

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
