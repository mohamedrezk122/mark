import asyncio

import click

from mark.server import Server, copy_selection, open_selection

db_files_arg = click.argument(
    "db_files", required=True, nargs=-1, type=click.Path(exists=True)
)
output_dir_opt = click.option(
    "-o", "-output", type=click.Path(), default="output", show_default=True
)
on_selection_opt = click.option(
    "--on-selection",
    default="copy",
    show_default=True,
    show_choices=True,
    type=click.Choice(["copy", "open"], case_sensitive=False),
    multiple=False,
)


async def execute_async_server(db_filename, mode, on_selection=None):
    async_server = Server(db_filename, mode=mode, on_selection=on_selection)
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
    on_selection_funcs = {
        "copy": copy_selection,
        "open": open_selection,
    }
    asyncio.run(
        execute_async_server(db_files, "read", on_selection_funcs[on_selection])
    )


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
