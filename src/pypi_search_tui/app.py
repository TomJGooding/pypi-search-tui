import webbrowser
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Input


@dataclass
class Package:
    name: str
    version: str
    description: str
    url: str


class PyPISearchApp(App):
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Container {
        height: 13;
        border: tall transparent;
    }
    """

    search_results: list[Package] = []

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search PyPI")
        with Container():
            yield DataTable(cursor_type="row")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value:
            self.search_pypi(event.value)

    @work(exclusive=True)
    async def search_pypi(self, value: str) -> None:
        self.search_results.clear()
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.loading = True

        url = f"https://pypi.org/search/?q={value}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)

        soup = BeautifulSoup(resp.content, "html.parser")
        for package in soup.find_all("a", class_="package-snippet"):
            url = f"https://pypi.org{package.get('href')}"
            name = package.find("span", class_="package-snippet__name").text
            version = package.find("span", class_="package-snippet__version").text
            description = package.find("p", class_="package-snippet__description").text
            self.search_results.append(Package(name, version, description, url))

        table.loading = False

        if not self.search_results:
            table.add_column(f"There were no results for '{value}'")

            # Add a temporary row as a workaround for
            # https://github.com/Textualize/textual/issues/4386
            # where new columns won't appear if the table is empty.
            table.add_row()
            table.clear()
            return

        table.add_columns(*("Name", "Version", "Description"))
        for package in self.search_results:
            table.add_row(
                package.name,
                package.version,
                package.description,
            )

        table.focus()

    @on(DataTable.RowSelected)
    def open_package_url(self, event: DataTable.RowSelected) -> None:
        url = self.search_results[event.cursor_row].url
        webbrowser.open(url)


def run() -> None:
    app = PyPISearchApp()
    app.run(inline=True)
