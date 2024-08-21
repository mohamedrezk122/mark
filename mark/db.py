import html
import time
from string import Template
from typing import Dict, List, Tuple

import orjson
from tinydb import Query, TinyDB

from mark.storage import FasterJSONStorage, YAMLStorage
from mark.utils import are_urls_equal, get_proper_write_mode


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
        # set the default title to url if the user didnot typed a title
        if title is None or not title.strip():
            title = url
        handle.insert({"title": title.strip(), "url": url})

    def insert_multiple(self, table: str, bookmark: List):
        handle = self.db.table(table)
        handle.insert_multiple(bookmark)

    def is_folder(self, table: str) -> bool:
        return table in self.db.tables()

    def get_bookmark(self, tablename: str, title: str) -> Tuple[str, str]:
        # TODO: handle title bein in path
        handle = self.db.table(tablename)
        return title, handle.get(Query().title == title)["url"]

    def bookmark_exists_in_table(self, tablename, url):
        handle = self.db.table(tablename)
        return handle.contains(Query().url.test(are_urls_equal, url))

    def list_raw_bookmarks(self, tablename: str) -> List:
        handle = self.db.table(tablename)
        all_rows = handle.all()
        for row in all_rows:
            title, url = row.get("title"), row.get("url")
            if not title:
                title = url
            yield (url, title)

    def list_bookmarks(
        self,
        tablename: str,
        template: Template = Template("$title"),
        meta: bool = False,
    ) -> Dict:
        mapping = dict()
        all_rows = self.list_raw_bookmarks(tablename)
        for url, title in all_rows:
            _title = template.safe_substitute(title=html.escape(title))
            if meta:
                mapping[_title] = (title, url)
            else:
                mapping[_title] = (title,)

        return mapping

    def list_raw_folders(self):
        return self.db.tables()

    def list_folders(self, template: Template = Template("$title")) -> List:
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
        if not db.is_folder(table):
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


def export_bookmarks_to_markdown(
    db_file: str, filepath: str, force: bool, heading: int
):

    assert 1 <= heading <= 6
    mode = "w" if force else "a+"
    file = open(filepath, mode)
    heading_level = "#" * heading

    def write_folder(folder_name, rows):
        folder_header = f"\n\n\n{heading_level} {folder_name}\n\n\n"
        file.write(folder_header)
        for url, title in rows:
            line = f"[{title}]({url})\n\n"
            file.write(line)

    db = DataBase(db_file)
    folders = db.list_raw_folders()
    for folder in folders:
        all_rows = db.list_raw_bookmarks(folder)
        write_folder(folder, all_rows)

    # force the data to os buffer
    file.flush()
    file.close()


def export_bookmarks_to_html(db_file: str, filepath: str, force: bool):
    header = """
    <!DOCTYPE NETSCAPE-Bookmark-file-1>
    <!--This is an automatically generated file.
    It will be read and overwritten.
    Do Not Edit! -->
    <Title>Bookmarks</Title>
    <H1>Bookmarks</H1>

    <DL>

    """
    header = "\n".join([line.lstrip() for line in header.split("\n")])
    db = DataBase(db_file)
    mode = "w" if force else get_proper_write_mode(filepath)
    file = open(filepath, mode)
    if mode == "w":
        file.write(header.strip())

    date = time.time()
    # common attrs used in all of the entries, better to pull it out of the loop
    attrs = 'ADD_DATE="{date}" LAST_MODIFIED="{date}" '
    # used in <A> tag
    misc = ' ICON_URI="" ICON="" '
    folder_header = Template(f"<DT><H3 {attrs}> $folder_name</H3>\n\t<DL><p>")
    folder_footer = "\t</DL><p>\n"
    bookmark_spec = Template(
        f"""
    <DT><A HREF="$url" ADD_DATE="{date}" LAST_VISIT="{date}"
    LAST_MODIFIED="{date}" {misc}>$title</A>\n"""
    )

    def write_folder(folder_name, rows):
        file.write(folder_header.substitute(folder_name=folder_name))
        for url, title in rows:
            file.write(bookmark_spec.substitute(url=url, title=title))
        file.write(folder_footer)

    folders = db.list_folders()
    for folder in folders:
        all_rows = db.list_raw_bookmarks(folder)
        write_folder(folder, all_rows)
    # end of file tag
    file.write("</DL>")
    file.flush()
    file.close()
