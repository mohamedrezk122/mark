from collections import defaultdict
from html.parser import HTMLParser


class BookmarkParser(HTMLParser):
    """Netscape bookmark file format parser to import bookmarks
    from other browsers
    """

    ignorable_tags = [None, "p", "meta", "h1", "title"]
    stack = []
    tag_stack = []
    bookmarks = defaultdict(list)

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
        url = list(filter(lambda x: x[0] == "href", attrs))[0][1]
        folder = self.stack[-1]
        self.bookmarks[folder].append({"url": url})

    def handle_endtag(self, tag):
        if self.__get_current_tag() in self.ignorable_tags:
            return
        if tag == "dl" and self.tag_stack[-1] == "dl":
            self.stack.pop()

        if tag == self.tag_stack[-1]:
            self.tag_stack.pop()

    def handle_data(self, data):
        tag = self.__get_current_tag()
        if not data.strip() or tag in self.ignorable_tags:
            return
        if tag == "h3":  # folder
            self.stack.append(data)
        elif tag == "a":
            self.bookmarks[self.stack[-1]][-1]["title"] = data

    def handle_decl(self, decl):
        pass


def parse_netscape_bookmark_file(filepath):
    parser = BookmarkParser()
    with open(filepath, "r") as file:
        # TODO: split the reading process (not reading the whole file at once)
        content = file.read()
        parser.feed(content)
    return parser.bookmarks
