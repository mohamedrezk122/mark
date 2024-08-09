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
    ):
        assert mode in ["read", "write"], "mode has to be 'read' or 'write'"
        self.mode = mode
        self.rofi = rofi_inst
        self.db = db
        self.on_selection = on_selection
        self.entry_format = entry_format
        # container for selection tracking
        self.mapping = None
        self.pack = {"current": "path"}

    def update_state(self, **kwargs):
        if "mapping" in kwargs:
            self.mapping = kwargs.pop("mapping")
        self.pack = {**self.pack, **kwargs}

    async def __close_connection(self, writer: asyncio.StreamWriter):
        writer.write(encode_message("quit"))
        await writer.drain()

    async def __handle_root_selection(self, writer: asyncio.StreamWriter, stitle: str):
        on_selection_funcs = {
            "copy": copy_selection,
            "open": open_selection,
        }
        stitle = self.mapping[stitle]
        title, url = self.db.get_bookmark(self.pack["path"], stitle)
        on_selection_funcs[self.on_selection](title, url)
        await self.__close_connection(writer)

    async def __handle_path_selection(self, writer: asyncio.StreamWriter, path: str):
        # TODO: handle hierarchical paths
        self.pack["path"] = self.mapping[path]
        self.mapping = self.db.list_bookmarks(self.pack["path"], self.entry_format)
        kwargs = {
            "message": f"<b>{self.pack["path"]}/</b>",
            "markup-rows": "true",
        }
        data = self.rofi.update_data(list(self.mapping.keys()), **kwargs)
        writer.write(data)
        await writer.drain()

    async def __handle_manual_bookmark_title(
        self, writer: asyncio.StreamWriter, url: str
    ):
        # TODO: handle hierarchical paths
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
        if self.pack["current"] == "path":
            # if path is not in mapping then it is new
            self.pack["path"] = self.mapping.get(value, value)
            if self.pack["title"] is None:
                self.pack["current"] = "title"
                await self.__handle_manual_bookmark_title(writer, self.pack["url"])
                return

        if self.pack["current"] == "title":
            if self.pack["title"] is None:
                self.pack["title"] = value

        self.db.insert_bookmark(self.pack["path"], self.pack["url"], self.pack["title"])
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
                if self.mode == "read" and not self.db.is_dir(self.mapping[res_value]):
                    await self.__handle_root_selection(writer, res_value)
                elif self.mode == "read":
                    await self.__handle_path_selection(writer, res_value)
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
        dir_format: str = "$title/",
        entry_format: str = "$title",
        infer_title: bool = False,
    ):
        entry_format_temp = Template(entry_format)
        dir_format_temp = Template(dir_format)
        port = Server.get_free_port()
        message = "choose or create dir" if mode == "write" else "choose dir"
        rofi = Rofi(message=f"<b>{message}</b>").setup_client(mode, port)
        db = DataBase(db_file)
        async_server = Server(
            db,
            mode=mode,
            rofi_inst=rofi,
            on_selection=on_selection,
            entry_format=entry_format_temp,
        )
        if mode == "write":
            url, title = get_url_and_title(infer_title)
            async_server.update_state(url=url, title=title)
        # set initial list of items
        async_server.update_state(mapping=db.list_dirs(template=dir_format_temp))
        await asyncio.gather(
            async_server.rofi.open_menu(list(async_server.mapping.keys())),
            async_server.run_server(port=port),
        )
