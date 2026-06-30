import re
from io import BytesIO
from html import unescape
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


class PDFReportService:
    @staticmethod
    def _strip_html(html: str) -> str:
        # Remove tags and normalize whitespace for PDF rendering.
        text = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</\s*li\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = unescape(text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    @staticmethod
    def _safe_filename(value: str) -> str:
        value = re.sub(r"[^\w\-. ]+", "", value, flags=re.UNICODE).strip()
        value = re.sub(r"\s+", "_", value)
        return value or "report"

    @staticmethod
    def generate_pdf_bytes(
        *,
        title: str,
        content: str,
        subtitle: Optional[str] = None,
        content_is_html: bool = False,
    ) -> bytes:
        """
        Generate a simple, readable PDF from text (or HTML stripped to text).
        Keeps implementation dependency-light (ReportLab only).
        """
        if content_is_html:
            content = PDFReportService._strip_html(content)

        buf = BytesIO()
        canvas = Canvas(buf, pagesize=A4)
        width, height = A4

        # Try to use a unicode-capable font if available (optional).
        # If it fails, fallback to Helvetica.
        font_name = "Helvetica"
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
            font_name = "DejaVuSans"
        except Exception:
            pass

        left = 2.0 * cm
        right = 2.0 * cm
        top = 2.0 * cm
        bottom = 2.0 * cm

        y = height - top
        canvas.setTitle(title)

        # Title
        canvas.setFont(font_name, 16)
        y -= 0.2 * cm
        canvas.drawString(left, y, title[:200])
        y -= 0.8 * cm

        # Subtitle
        if subtitle:
            canvas.setFont(font_name, 10)
            canvas.drawString(left, y, subtitle[:300])
            y -= 0.8 * cm

        # Body
        canvas.setFont(font_name, 10)
        line_height = 14
        max_width = width - left - right

        def wrap_line(s: str) -> list[str]:
            if not s:
                return [""]
            words = s.split()
            lines: list[str] = []
            cur = ""
            for w in words:
                test = (cur + " " + w).strip()
                if canvas.stringWidth(test, font_name, 10) <= max_width:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines or [""]

        for raw_line in content.split("\n"):
            for line in wrap_line(raw_line):
                if y <= bottom:
                    canvas.showPage()
                    canvas.setFont(font_name, 10)
                    y = height - top
                canvas.drawString(left, y, line)
                y -= line_height

        canvas.save()
        return buf.getvalue()

