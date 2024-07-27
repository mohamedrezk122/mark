import asyncio

import click

from mark.db import DataBase
from mark.rofi import Rofi
from mark.server import Server
from mark.utils import get_free_port

db_files_arg = click.argument(
    "db_files", required=True, nargs=-1, type=click.Path(exists=True)
)
output_file_opt = click.option(
    "-o", "--output", type=click.Path(), default="merged.yaml", show_default=True
)
on_selection_opt = click.option(
    "--on-selection",
    default="copy",
    show_default=True,
    show_choices=True,
    type=click.Choice(["copy", "open"], case_sensitive=False),
    multiple=False,
)


async def execute_async_server(db_filename: str, mode: str, on_selection: str = None):
    if mode == "write":
        import pyperclip

        url = pyperclip.paste()
    port = get_free_port()
    message = "choose or create dir" if mode == "read" else "choose dir"
    rofi = Rofi(message=message).setup_client(mode, port)
    db = DataBase(db_filename)
    async_server = Server(
        port, db, mode=mode, rofi_inst=rofi, on_selection=on_selection, url=url
    )

    await asyncio.gather(
        async_server.rofi.open_menu(async_server.db.list_dirs()),
        async_server.run_server(),
    )


@click.group()
def cli():
    """
    Your Swiss Army knife for global bookmark management
    """
    pass


@cli.command("get")
@db_files_arg
@on_selection_opt
def mark_get_bookmark(db_files, on_selection):
    """
    Retrieve a bookmark
    """
    # TODO: handle multiple files
    db_files = db_files[0]
    asyncio.run(execute_async_server(db_files, "read", on_selection))


@cli.command("insert")
@db_files_arg
def mark_insert_bookmark(db_files):
    """
    Insert a bookmark
    """
    # TODO: handle multiple files
    db_files = db_files[0]
    asyncio.run(execute_async_server(db_files, "write"))


if __name__ == "__main__":
    cli()
