import asyncio
import json
import socket
from contextlib import closing
from string import Template

from tinydb import TinyDB

from mark.db import DataBase
from mark.rofi import Rofi
from mark.utils import (
    copy_selection,
    decode_message,
    encode_message,
    get_url_and_title,
    open_selection,
)


class Server:
    def __init__(
        self,
        db: TinyDB,
        mode: str = "read",
        rofi_inst: Rofi = None,
        on_selection: str = None,
        bookmark: tuple = None,
        entry_format: Template = None,
        url_meta: bool = False,
        no_duplicates: bool = False,
    ):
        assert mode in ["read", "write"], "mode has to be 'read' or 'write'"
        self.mode = mode
        self.rofi = rofi_inst
        self.db = db
        self.on_selection = on_selection
        self.entry_format = entry_format
        # container for selection tracking
        self.mapping = None
        self.pack = {"current": "folder"}
        self.url_meta = url_meta
        self.no_duplicates = no_duplicates

    def update_state(self, **kwargs):
        if "mapping" in kwargs:
            self.mapping = kwargs.pop("mapping")
        self.pack = {**self.pack, **kwargs}

    async def __close_connection(self, writer: asyncio.StreamWriter):
        writer.write(encode_message("quit"))
        await writer.drain()
        self.rofi.kill_proc()

    async def __handle_root_selection(self, writer: asyncio.StreamWriter, stitle: str):
        on_selection_funcs = {
            "copy": copy_selection,
            "open": open_selection,
        }
        title = self.mapping[stitle][0]
        if not self.url_meta:
            _, url = self.db.get_bookmark(self.pack["folder"], title)
        else:
            url = self.mapping[stitle][1]
        on_selection_funcs[self.on_selection](title, url)
        await self.__close_connection(writer)

    async def __handle_folder_selection(
        self, writer: asyncio.StreamWriter, folder: str
    ):
        self.pack["folder"] = self.mapping[folder]
        self.mapping = self.db.list_bookmarks(
            self.pack["folder"], self.entry_format, meta=self.url_meta
        )
        kwargs = {
            "message": "<b>%s/</b>" % self.pack["folder"],
            "markup-rows": "true",
        }
        if self.url_meta:
            items = [(title, value[1]) for title, value in self.mapping.items()]
        else:
            items = list(self.mapping.keys())

        data = self.rofi.update_data(items, meta=self.url_meta, **kwargs)
        writer.write(data)
        await writer.drain()

    async def __handle_manual_bookmark_title(
        self, writer: asyncio.StreamWriter, url: str
    ):
        kwargs = {
            "prompt": "title",
            "message": url,
        }
        data = self.rofi.update_data(None, **kwargs)
        writer.write(data)
        await writer.drain()

    async def __handle_bookmark_insertion(
        self, writer: asyncio.StreamWriter, value: str
    ):
        if self.pack["current"] == "folder":
            # if folder is not in mapping then it is new
            self.pack["folder"] = self.mapping.get(value, value)
            if self.no_duplicates and self.db.bookmark_exists_in_table(
                self.pack["folder"], self.pack["url"]
            ):
                print(f"bookmark is already there under %s" % self.pack["folder"])
                await self.__close_connection(writer)
                return
            if self.pack["title"] is None:
                self.pack["current"] = "title"
                await self.__handle_manual_bookmark_title(writer, self.pack["url"])
                return

        if self.pack["current"] == "title":
            self.pack["title"] = value

        self.db.insert_bookmark(
            self.pack["folder"], self.pack["url"], self.pack["title"]
        )
        await self.__close_connection(writer)

    async def __handle_readwrite_mode(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        while True:
            if self.rofi.server_should_exit:
                quit()
            try:
                await asyncio.sleep(0)
                response = await reader.read(4096)
                # response format -> {"code": return_code, "value": selected_item}
                if response is None:
                    continue
                response = json.loads(decode_message(response))
                res_value = response["value"]
                entry = self.mapping.get(res_value, res_value)
                p = entry[0] if len(entry) == 2 else entry
                if self.mode == "read" and not self.db.is_folder(p):
                    await self.__handle_root_selection(writer, res_value)
                elif self.mode == "read":
                    await self.__handle_folder_selection(writer, res_value)
                elif self.mode == "write":
                    await self.__handle_bookmark_insertion(writer, res_value)
            except json.JSONDecodeError:
                continue
        writer.close()
        await writer.wait_closed()

    async def run_server(self, port):
        server = await asyncio.start_server(
            self.__handle_readwrite_mode, host="localhost", port=port
        )
        async with server:
            await server.serve_forever()

    @staticmethod
    def get_free_port():
        # avoid hard-coded ports
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as soc:
            # choose an available port by passing 0
            soc.bind(("localhost", 0))
            # allow port reuse
            soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return soc.getsockname()[1]

    @staticmethod
    async def execute_async_server(
        db_file: str,
        mode: str,
        on_selection: str = None,
        folder_format: str = "$title/",
        entry_format: str = "$title",
        infer_title: bool = False,
        no_duplicates: bool = False,
        url_meta: bool = False,
    ):
        entry_format_temp = Template(entry_format)
        folder_format_temp = Template(folder_format)
        port = Server.get_free_port()
        message = "choose or create folder" if mode == "write" else "choose folder"
        rofi = Rofi(message=f"<b>{message}</b>").setup_client(mode, port)
        db = DataBase(db_file)
        async_server = Server(
            db,
            mode=mode,
            rofi_inst=rofi,
            on_selection=on_selection,
            entry_format=entry_format_temp,
            url_meta=url_meta,
            no_duplicates=no_duplicates,
        )
        if mode == "write":
            url, title = get_url_and_title(infer_title)
            async_server.update_state(url=url, title=title)
        # set initial list of items
        async_server.update_state(mapping=db.list_folders(template=folder_format_temp))
        await asyncio.gather(
            async_server.rofi.open_menu(list(async_server.mapping.keys())),
            async_server.run_server(port=port),
        )
