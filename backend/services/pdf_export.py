import io
import logging

try:
    from weasyprint import HTML
    WEASYPRINT_INSTALLED = True
except ImportError:
    WEASYPRINT_INSTALLED = False

try:
    from pypdf import PdfReader, PdfWriter
    PDF_MERGER_INSTALLED = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        PDF_MERGER_INSTALLED = True
    except ImportError:
        PDF_MERGER_INSTALLED = False

logger = logging.getLogger("ats_resume_scorer")

def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    """Render each HTML report and combine the resulting PDFs into one file."""
    if not WEASYPRINT_INSTALLED:
        raise ImportError("WeasyPrint is not installed. PDF generation unavailable.")
    if not PDF_MERGER_INSTALLED:
        raise ImportError("pypdf/PyPDF2 is not installed. PDF merging unavailable.")
    if not html_docs:
        raise ValueError("No report content was provided.")

    writer = PdfWriter()
    for name, html_str in html_docs.items():
        if not html_str:
            continue
        pdf_bytes = HTML(string=html_str).write_pdf()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    if len(writer.pages) == 0:
        raise ValueError("No PDF pages were generated from the report templates.")

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
