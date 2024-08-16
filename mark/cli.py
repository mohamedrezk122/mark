import asyncio

import click
from click.core import ParameterSource

from mark.db import (
    export_bookmarks_to_html,
    export_bookmarks_to_markdown,
    save_bookmarks_to_db,
)
from mark.parser import parse_netscape_bookmark_file
from mark.server import Server

db_file_arg = click.argument(
    "db_file",
    required=True,
    type=click.Path(exists=True),
)
db_file_write_arg = click.argument(
    "db_file",
    required=True,
    type=click.Path(),
)
output_file_opt = click.option(
    "-o",
    "--output",
    type=click.Path(),
    default="output",
    show_default=True,
    help="output file path",
)
on_selection_opt = click.option(
    "--on-selection",
    default="copy",
    show_default=True,
    show_choices=True,
    type=click.Choice(["copy", "open"], case_sensitive=False),
    multiple=False,
    help=(
        "Action upon selection of a bookmark, currently `open` in default application"
        " or `copy` url"
    ),
)
format_opt = click.option(
    "--format",
    default="html",
    show_default=True,
    show_choices=True,
    type=click.Choice(["html", "md"], case_sensitive=False),
    help="explicit file format used in import and export",
)
start_date_opt = click.option(
    "--start-date",
    default=None,
    show_default=True,
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m", "%Y"]),
    help="start date at which you want to filter bookmarks",
)
end_date_opt = click.option(
    "--end-date",
    default=None,
    show_default=True,
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m", "%Y"]),
    help="end date at which you want to filter bookmarks",
)
date_attr_opt = click.option(
    "--date-attr",
    type=click.Choice(["add", "modify"]),
    default="add",
    show_default=True,
    show_choices=True,
    help="kind of date used in filtering, either add_date or last_modified",
)
bookmark_file_arg = click.argument(
    "file",
    type=click.Path(exists=True),
    # help="bookmark file you want to import from, either markdown or html",
)
dir_format_opt = click.option(
    "--dir-format",
    type=click.STRING,
    default="$title/",
    show_default=True,
    help="pango formatting str used to change the style of folder entry in rofi",
)
entry_format_opt = click.option(
    "--entry-format",
    type=click.STRING,
    default="$title",
    show_default=True,
    help="pango formatting str used to change the style of bookmark entry in rofi",
)
clean_opt = click.option(
    "--clean-title", is_flag=True, help="flag to enable title cleaning during import"
)
infer_title = click.option(
    "--infer-title",
    is_flag=True,
    help="flag to enable title inference during insertion",
)
no_duplicates = click.option(
    "--no-duplicates", is_flag=True, help="flag to prune duplicates during import"
)
force = click.option(
    "--force", is_flag=True, help="flag to force write on existing files"
)
remove_if_empty = click.option(
    "--remove-if-empty",
    is_flag=True,
    help=(
        "flag to remove empty folder if they don't contain any bookmarks during import"
    ),
)
url_meta = click.option(
    "--url-meta",
    is_flag=True,
    help="use url as a hidden search term to filter bookmarks with",
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
@dir_format_opt
@entry_format_opt
@url_meta
def mark_get_bookmark(db_file, on_selection, dir_format, entry_format, url_meta):
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
            url_meta=url_meta,
        )
    )


@cli.command("insert")
@db_file_write_arg
@dir_format_opt
@infer_title
@no_duplicates
def mark_insert_bookmark(db_file, dir_format, infer_title, no_duplicates):
    """
    Insert a bookmark
    """
    # TODO: handle multiple files
    asyncio.run(
        Server.execute_async_server(
            db_file,
            mode="write",
            dir_format=dir_format,
            infer_title=infer_title,
            no_duplicates=no_duplicates,
        )
    )


@cli.command("import")
@bookmark_file_arg
@format_opt
@output_file_opt
@clean_opt
@no_duplicates
@start_date_opt
@end_date_opt
@date_attr_opt
@remove_if_empty
def mark_import_bookmarks(
    file,
    format,
    output,
    clean_title,
    no_duplicates,
    start_date,
    end_date,
    date_attr,
    remove_if_empty,
):
    """
    Import bookmarks from other browsers
    """
    if not is_default_option("end_date") and not is_default_option("start_date"):
        assert start_date < end_date, "end-date should be after start-date"

    if format == "html":
        flags = {
            "clean_title": clean_title,
            "remove_if_empty": remove_if_empty,
        }
        bookmarks = parse_netscape_bookmark_file(
            file, (start_date, end_date), date_attr, flags
        )
    else:
        raise NotImplementedError("Not yet implemented for markdown")

    if is_default_option("output"):
        output = "imported_bookmarks.json"

    save_bookmarks_to_db(bookmarks, output, no_duplicates)


@cli.command("export")
@db_file_arg
@format_opt
@output_file_opt
@force
def mark_export_bookmarks(db_file, format, output, force):
    """
    Export bookmarks to html or markdown
    """

    if is_default_option("output"):
        output = f"exported_bookmarks.{format}"
    else:
        if not output.endswith(format):
            output = f"{output}.{format}"

    if format == "md":
        export_bookmarks_to_markdown(db_file, output, force, heading=3)
    elif format == "html":
        export_bookmarks_to_html(db_file, output, force)


if __name__ == "__main__":
    cli()
