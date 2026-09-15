#!/usr/bin/env python
"""RESULTS.md -> docs/results/index.html (GitHub Pages) and copy the referenced PNG maps to docs/results/img."""
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
HEAD = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Wrights Road breach model – results</title>\n'
        '<style>body{font-family:"IBM Plex Sans",system-ui,sans-serif;background:#0d1117;color:#e7ebf1;margin:0;padding:32px 20px 64px;'
        'max-width:1100px;margin-inline:auto;line-height:1.5}h1{font-size:26px}h2{margin-top:40px;border-bottom:1px solid #2a3442;padding-bottom:6px}'
        'a{color:#8fd3ff}table{border-collapse:collapse;font-size:13.5px;display:block;overflow-x:auto}th,td{border:1px solid #2a3442;padding:5px 9px;'
        'text-align:left}th{background:#151b24}img{max-width:100%;border:1px solid #2a3442;border-radius:6px;margin:6px 0 18px;background:#fff}'
        'p{max-width:80ch}.nav{margin-bottom:24px;color:#9aa4b5}</style>\n'
        '<div class="nav"><a href="../">← Animations</a> · <a href="https://github.com/ThorstenBux/wrights-road-dam-breach">Repository</a></div>\n')
GH = "https://github.com/ThorstenBux/wrights-road-dam-breach/blob/main/"


def main():
    md = (ROOT / "RESULTS.md").read_text()
    out = ROOT / "docs" / "results"; img = out / "img"; img.mkdir(parents=True, exist_ok=True)
    def repl(m):
        src = Path(m.group(2)); sc = src.parts[1]; dst = img / f"{sc}_{src.name}"
        if (ROOT / src).exists():
            shutil.copy(ROOT / src, dst)
        return f"![{m.group(1)}](img/{dst.name})"
    md = re.sub(r"!\[([^\]]*)\]\((outputs/[^)]+\.png)\)", repl, md)
    md = re.sub(r"\]\(((?:SPEC|HANDOVER|README)\.md|docs/[^)]+\.md)([^)]*)\)", lambda m: f"]({GH}{m.group(1)}{m.group(2)})", md)
    html = markdown.markdown(md, extensions=["tables"])
    (out / "index.html").write_text(HEAD + html + "\n")
    print(f"wrote {out/'index.html'} ({len(html)/1e3:.0f} kB)")


if __name__ == "__main__":
    main()
