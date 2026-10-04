"""Dashboard rendering (HTML) and PDF export."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


class HtmlBuilder:
    """Renders an HTML template into one self-contained file: every assets/*.css and assets/*.js
    reference is inlined and the JSON payload is injected, so the output works offline."""

    DATA_TOKEN = "/*__DATA__*/null"
    CSS_LINK = re.compile(r'<link rel="stylesheet" href="assets/([\w.-]+\.css)">')
    JS_TAG = re.compile(r'<script src="assets/([\w.-]+\.js)"></script>')

    def __init__(self, template_dir: Path):
        self.template_dir = Path(template_dir)
        self.assets = self.template_dir / "assets"

    def _asset(self, name: str) -> str:
        return (self.assets / name).read_text(encoding="utf-8")

    def render(self, template: str, payload: dict) -> str:
        html = (self.template_dir / template).read_text(encoding="utf-8")
        html = self.CSS_LINK.sub(lambda m: f"<style>\n{self._asset(m.group(1))}\n</style>", html)
        html = self.JS_TAG.sub(lambda m: f"<script>\n{self._asset(m.group(1))}\n</script>", html)
        if self.DATA_TOKEN not in html:
            raise ValueError(f"{template} is missing the data placeholder")
        return html.replace(self.DATA_TOKEN, json.dumps(payload, ensure_ascii=False, default=float))

    def save(self, template: str, payload: dict, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(template, payload), encoding="utf-8")
        return path


class PdfExporter:
    """Prints the dashboard to PDF with a headless Chromium browser (Edge or Chrome)."""

    CANDIDATES = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "msedge", "google-chrome", "chromium", "chrome",
    ]

    def __init__(self, browser: str | None = None):
        self.browser = browser or self._find_browser()

    def _find_browser(self) -> str | None:
        for c in self.CANDIDATES:
            if Path(c).exists() or shutil.which(c):
                return c
        return None

    def export(self, html_path: Path, pdf_path: Path) -> Path | None:
        if not self.browser:
            print("No Chromium browser found - skipping PDF export.")
            return None
        subprocess.run([self.browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        "--virtual-time-budget=5000", f"--print-to-pdf={pdf_path}",
                        Path(html_path).resolve().as_uri()],
                       check=True, capture_output=True, timeout=180)
        return pdf_path
