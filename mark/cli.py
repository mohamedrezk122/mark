import asyncio

import click

from mark.db import insert_multiple_bookmarks
from mark.parser import parse_netscape_bookmark_file
from mark.server import execute_async_server

db_files_arg = click.argument(
    "db_files", required=True, nargs=-1, type=click.Path(exists=True)
)
output_file_opt = click.option(
    "-o", "--output", type=click.Path(), default="output.yaml", show_default=True
)
on_selection_opt = click.option(
    "--on-selection",
    default="copy",
    show_default=True,
    show_choices=True,
    type=click.Choice(["copy", "open"], case_sensitive=False),
    multiple=False,
)
format_opt = click.option(
    "-f",
    "--format",
    default="html",
    show_default=True,
    show_choices=True,
    type=click.Choice(["html", "markdown"], case_sensitive=False),
)
bookmark_file_arg = click.argument(
    "file",
    type=click.Path(exists=True),
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


@cli.command("import")
@bookmark_file_arg
@format_opt
@output_file_opt
def mark_import_bookmarks(file, format, output):
    """
    Import bookmarks from other browsers
    """
    if format == "html":
        bookmarks = parse_netscape_bookmark_file(file)
    else:
        raise NotImplementedError()

    insert_multiple_bookmarks(bookmarks, output)


if __name__ == "__main__":
    cli()
