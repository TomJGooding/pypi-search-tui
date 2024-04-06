import argparse
import webbrowser
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Input


@dataclass
class Package:
    name: str
    version: str
    description: str
    url: str


class SearchResultsTable(DataTable):
    BINDINGS = [
        Binding("enter", "select_cursor", "View on PyPI", show=True),
        Binding("up,k", "cursor_up", "Cursor Up", show=False),
        Binding("down,j", "cursor_down", "Cursor Down", show=False),
    ]


class PyPISearchApp(App):
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
    ]

    CSS = """
    Container {
        height: 13;
        border: tall transparent;
    }

    LoadingIndicator {
        background: transparent;
    }
    """

    search_results: list[Package] = []

    def __init__(
        self,
        initial_query: str | None = None,
    ):
        super().__init__()
        self.initial_query = initial_query

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search PyPI", value=self.initial_query)
        with Container():
            yield SearchResultsTable(cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        if self.initial_query:
            self.search_pypi(self.initial_query)

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value:
            self.search_pypi(event.value)

    @work(exclusive=True)
    async def search_pypi(self, query: str) -> None:
        self.search_results.clear()
        table = self.query_one(SearchResultsTable)
        table.clear(columns=True)
        table.loading = True

        url = "https://pypi.org/search/"
        params = {"q": query}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)

        soup = BeautifulSoup(resp.content, "html.parser")
        for package in soup.find_all("a", class_="package-snippet"):
            url = f"https://pypi.org{package.get('href')}"
            name = package.find("span", class_="package-snippet__name").text
            version = package.find("span", class_="package-snippet__version").text
            description = package.find("p", class_="package-snippet__description").text
            self.search_results.append(Package(name, version, description, url))

        table.loading = False

        if not self.search_results:
            table.can_focus = False
            table.add_column(f"There were no results for '{query}'")

            # Add a temporary row as a workaround for
            # https://github.com/Textualize/textual/issues/4386
            # where new columns won't appear if the table is empty.
            table.add_row()
            table.clear()
            return

        table.can_focus = True
        table.add_columns(*("Name", "Version", "Description"))
        for package in self.search_results:
            table.add_row(
                package.name,
                package.version,
                package.description,
            )

        table.focus()

    @on(SearchResultsTable.RowSelected)
    def open_url_in_browser(self, event: SearchResultsTable.RowSelected) -> None:
        url = self.search_results[event.cursor_row].url
        webbrowser.open(url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pypi-search-tui",
        description="Search Python packages from your terminal",
    )
    parser.add_argument(
        "query",
        help="Search terms to find packages on PyPI",
        nargs="*",
        type=str,
    )
    return parser.parse_args()


def run() -> None:
    args = parse_args()
    query = " ".join(args.query) if args.query else None
    app = PyPISearchApp(initial_query=query)
    app.run(inline=True)
