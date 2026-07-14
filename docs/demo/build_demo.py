# -*- coding: utf-8 -*-
"""Gera docs/demo/index.html e standalone.html a partir de web/."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
DEMO = ROOT / "docs" / "demo"
DEMO.mkdir(parents=True, exist_ok=True)

web = (WEB / "index.html").read_text(encoding="utf-8")
web = web.replace(
    "<title>Ferrari IoT — Postdoc Lab</title>",
    "<title>Ferrari IoT — Demo Lab (GitHub Pages)</title>",
)
web = web.replace('href="/static/style.css"', 'href="./style.css"')
web = web.replace(
    '<script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>\n  ',
    "",
)
web = web.replace(
    '<script src="/static/audio.js"></script>',
    '<script src="./audio.js"></script>',
)
web = web.replace('<script src="/static/vision.js"></script>\n  ', "")
web = web.replace(
    '<script src="/static/script.js"></script>',
    '<script src="./demo.js"></script>',
)
web = web.replace(
    "<p>Pós em Engenharia da Computação · Arduino ↔ Raspberry</p>",
    "<p>Demo Lab (GitHub Pages) · Arduino ↔ Raspberry · sem backend</p>",
)
(DEMO / "index.html").write_text(web, encoding="utf-8")

css = (DEMO / "style.css").read_text(encoding="utf-8")
audio = (DEMO / "audio.js").read_text(encoding="utf-8")
demo_js = (DEMO / "demo.js").read_text(encoding="utf-8")
body = re.search(r"<body>(.*)</body>", web, re.S).group(1)
body = re.sub(r'\s*<script src="[^"]+"></script>', "", body)

standalone = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ferrari IoT — Demo Lab (GitHub Pages)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Archivo+Narrow:wght@600;700&family=Archivo:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
{css}
  </style>
</head>
<body>
{body}
  <script>
{audio}
  </script>
  <script>
{demo_js}
  </script>
</body>
</html>
"""
(DEMO / "standalone.html").write_text(standalone, encoding="utf-8")
print("OK index", (DEMO / "index.html").stat().st_size)
print("OK standalone", (DEMO / "standalone.html").stat().st_size)
