"""Report generation tool."""


class MarkdownGenerator:
    """Markdown report generator."""

    def __init__(self):
        self.content = ""

    def add_heading(self, text: str, level: int = 1) -> None:
        pass

    def add_paragraph(self, text: str) -> None:
        pass

    def add_table(self, headers: list, rows: list) -> None:
        pass

    def build(self) -> str:
        return self.content


async def generate_markdown(
    job_name: str = "",
    receptor_name: str = "",
    top_results: list = None,
    analysis_result: dict = None,
) -> str:
    """Generate Markdown report."""
    return "# Report"


async def generate_pdf(markdown_content: str = "", output_path: str = None) -> str:
    """Generate PDF from markdown."""
    return "/output/report.pdf"


async def generate_html(markdown_content: str = "", output_path: str = None) -> str:
    """Generate HTML from markdown."""
    return "/output/report.html"
