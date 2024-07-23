from typing import List, Tuple

from tinydb import Query, TinyDB

from mark.storage import YAMLStorage


class DataBase:
    def __init__(self, filetitle: str, trailing_char: str = "\\"):
        assert len(trailing_char) == 1
        self.db = TinyDB(filetitle, storage=YAMLStorage)
        self.trailing_char = trailing_char

    def insert_bookmark(self, table: str, bookmark_title: str, url: str):
        table = self.__handle_path(table)
        handle = self.db.table(table)
        handle.insert({"title": bookmark_title, "url": url})

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
        handle = self.db.table(table)
        all_rows = handle.all()
        parent = f"{table}{self.trailing_char}" if is_full else ""
        attrs = ["%s%s" % (parent, row.get("title")) for row in all_rows]
        return attrs

    def list_dirs(self) -> List:
        return [f"{table}{self.trailing_char}" for table in self.db.tables()]
