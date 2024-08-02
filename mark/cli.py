import asyncio

import click
from click.core import ParameterSource

from mark.db import export_bookmarks_to_markdown, save_bookmarks_to_db
from mark.parser import parse_netscape_bookmark_file
from mark.server import execute_async_server

db_file_arg = click.argument("db_file", required=True, type=click.Path(exists=True))
output_file_opt = click.option(
    "-o", "--output", type=click.Path(), default="output", show_default=True
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
    type=click.Choice(["html", "md"], case_sensitive=False),
)
bookmark_file_arg = click.argument(
    "file",
    type=click.Path(exists=True),
)


def is_default_option(param):
    """
    Return true if the click option is not passed to cmd, and the default value
    is used
    """
    parameter_source = click.get_current_context().get_parameter_source(param)
    return parameter_source == ParameterSource.DEFAULT


@click.group()
def cli():
    """
    Your Swiss Army knife for global bookmark management
    """
    pass


@cli.command("get")
@db_file_arg
@on_selection_opt
def mark_get_bookmark(db_file, on_selection):
    """
    Retrieve a bookmark
    """
    # TODO: handle multiple files
    asyncio.run(execute_async_server(db_file, "read", on_selection))


@cli.command("insert")
@db_file_arg
def mark_insert_bookmark(db_file):
    """
    Insert a bookmark
    """
    # TODO: handle multiple files
    asyncio.run(execute_async_server(db_file, "write"))


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
        raise NotImplementedError("Not yet implemented for markdown")

    if is_default_option("output"):
        output = "imported_bookmarks.json"

    save_bookmarks_to_db(bookmarks, output)


@cli.command("export")
@db_file_arg
@format_opt
@output_file_opt
def mark_export_bookmarks(db_file, format, output):
    """
    Export bookmarks to html or markdown
    """

    if is_default_option("output"):
        output = f"exported_bookmarks.{format}"
    else:
        if not output.endswith(format):
            output = f"{output}.{format}"

    if format == "md":
        export_bookmarks_to_markdown(db_file, output, heading=3)
    else:
        raise NotImplementedError("Not yet implemented for html")


if __name__ == "__main__":
    cli()
