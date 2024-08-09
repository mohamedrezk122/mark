import asyncio

import click
from click.core import ParameterSource

from mark.db import export_bookmarks_to_markdown, save_bookmarks_to_db
from mark.parser import parse_netscape_bookmark_file
from mark.server import Server

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
dir_format_opt = click.option(
    "--dir-format", type=click.STRING, default="$title/", show_default=True
)
entry_format_opt = click.option(
    "--entry-format", type=click.STRING, default="$title", show_default=True
)
clean_opt = click.option("--clean-title", is_flag=True)
infer_title = click.option("--infer-title", is_flag=True)
no_duplicates = click.option("--no-duplicates", is_flag=True)


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
@dir_format_opt
@entry_format_opt
def mark_get_bookmark(db_file, on_selection, dir_format, entry_format):
    """
    Retrieve a bookmark
    """
    # TODO: handle multiple files
    asyncio.run(
        Server.execute_async_server(
            db_file=db_file,
            mode="read",
            on_selection=on_selection,
            dir_format=dir_format,
            entry_format=entry_format,
        )
    )


@cli.command("insert")
@db_file_arg
@dir_format_opt
@infer_title
def mark_insert_bookmark(db_file, dir_format, infer_title):
    """
    Insert a bookmark
    """
    # TODO: handle multiple files
    asyncio.run(
        Server.execute_async_server(
            db_file, mode="write", dir_format=dir_format, infer_title=infer_title
        )
    )


@cli.command("import")
@bookmark_file_arg
@format_opt
@output_file_opt
@clean_opt
@no_duplicates
def mark_import_bookmarks(file, format, output, clean_title, no_duplicates):
    """
    Import bookmarks from other browsers
    """
    if format == "html":
        bookmarks = parse_netscape_bookmark_file(file, clean_title)
    else:
        raise NotImplementedError("Not yet implemented for markdown")

    if is_default_option("output"):
        output = "imported_bookmarks.json"

    save_bookmarks_to_db(bookmarks, output, no_duplicates)


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
