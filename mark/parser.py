import functools
from collections import defaultdict
from html.parser import HTMLParser
from typing import Dict

from mark.utils import clean_bookmark_title, filter_by_date


def filter_attr(attrs, key):
    query = list(filter(lambda x: x[0] == key, attrs))
    return query[0][1] if query else None


class BookmarkParser(HTMLParser):
    """Netscape bookmark file format parser to import bookmarks
    from other browsers
    """

    def __init__(self, date_attr: str, filters: Dict, flags: Dict):
        super().__init__()
        self.ignorable_tags = [None, "p", "meta", "h1", "title"]
        self.folder_stack = []
        self.tag_stack = []
        self.bookmarks = defaultdict(list)
        self.date_attr = {"add": "add_date", "modify": "last_modified"}[date_attr]
        self.filters = filters
        self.flags = flags

    def __get_current_tag(self):
        raw_tag = self.get_starttag_text()
        if not raw_tag:
            return
        return raw_tag.strip("<>").split(" ")[0].lower()

    def handle_starttag(self, tag, attrs):
        if tag in self.ignorable_tags:
            return
        self.tag_stack.append(tag)
        if tag != "a":
            return
        url = filter_attr(attrs, "href")
        folder = self.folder_stack[-1]
        self.bookmarks[folder].append({})
        if "date" in self.filters:
            date = int(filter_attr(attrs, self.date_attr))
            if not self.filters["date"](date):
                return
        self.bookmarks[folder][-1]["url"] = url

    def handle_endtag(self, tag):
        if self.__get_current_tag() in self.ignorable_tags:
            return

        if tag == "dl" and self.tag_stack[-1] == "dl":
            self.tag_stack.pop()

        if tag == self.tag_stack[-1]:
            self.tag_stack.pop()

    def handle_data(self, data):
        tag = self.__get_current_tag()
        if tag in self.ignorable_tags:
            return
        if tag == "h3":  # folder
            if not data.strip():
                return
            # remove previous folder if it has no entries and user chose so
            if self.flags["remove_if_empty"] and self.folder_stack:
                f = self.folder_stack[-1]
                if f in self.bookmarks and not self.bookmarks[f]:
                    self.bookmarks.pop(f)
            self.folder_stack.append(data)
        elif tag == "a":
            folder = self.bookmarks[self.folder_stack[-1]]
            if not folder:
                return
            # url is filtered out so skip title
            if "url" not in folder[-1]:
                folder.pop()  # delete this empty enrty
                return
            if not data.strip():
                return
            res = clean_bookmark_title(data) if self.flags["clean_title"] else data
            if not res.strip():
                # default title to the url
                res = folder[-1]["url"]
            folder[-1]["title"] = res


def parse_netscape_bookmark_file(filepath, date_range, date_attr, flags):
    start_date, end_date = date_range
    date_filter = functools.partial(
        filter_by_date, start_date=start_date, end_date=end_date
    )
    parser = BookmarkParser(
        date_attr=date_attr, filters={"date": date_filter}, flags=flags
    )
    with open(filepath, "r") as file:
        # TODO: split the reading process (not reading the whole file at once)
        content = file.read()
        parser.feed(content)
    return parser.bookmarks
