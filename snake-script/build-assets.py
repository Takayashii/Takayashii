"""Renders the README's SVG panels with Sen embedded as a subset webfont.

GitHub strips <style> from inline SVG and blocks external fetches from an
<img>, so the only way to actually get Sen — rather than whatever sans-serif
the reader happens to have — is to instance the variable font at one weight,
subset it to the glyphs these panels use, and inline it as a data: URI.

    pip install fonttools brotli
    python scripts/build-assets.py
"""

import base64
import io
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".fontcache" / "sen.ttf"
OUT = ROOT / "assets"
SOURCE = "https://github.com/google/fonts/raw/main/ofl/sen/Sen%5Bwght%5D.ttf"

# --- content -----------------------------------------------------------------

NAME = "Takayashii"
HANDLE = "@takayashii"
TAGLINE = "Full stack developer · Graphics Designer · Video Editor"
META = [
    ("Debuff Network", "fg"),
    ("debuff.club", "accent"),
    ("debuff.contact@gmail.com", "muted"),
]

STACK = [
    ("LANGS", ["Java", "TypeScript", "JavaScript", "Python", "PHP", "C", "C++", "C#"]),
    ("FRONTEND", ["React", "Next.js", "HTML", "CSS"]),
    ("BACKEND", ["Node.js", "Express", "MySQL", "MongoDB", "Redis"]),
    ("DEVOPS", ["Docker", "Ubuntu", "Nginx", "Caddy", "Cloudflare", "Pterodactyl"]),
]

THEMES = {
    "dark": {"fg": "#e6edf3", "muted": "#8b949e", "rule": "#21262d", "accent": "#e02424"},
    "light": {"fg": "#1f2328", "muted": "#59636e", "rule": "#d0d7de", "accent": "#bb0000"},
}

W = 1200
PAD = 48

# --- font --------------------------------------------------------------------


def font_data_uri(weight: int, glyphs: str) -> str:
    """Instances Sen at one weight, keeps only `glyphs`, returns a woff2 data URI."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["curl", "-sL", "-o", str(CACHE), SOURCE], check=True)

    font = instantiateVariableFont(TTFont(CACHE), {"wght": weight}, inplace=False)

    options = subset.Options(flavor="woff2", desubroutinize=True)
    options.layout_features = ["kern", "liga"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=glyphs)
    subsetter.subset(font)

    buf = io.BytesIO()
    font.save(buf)
    return "data:font/woff2;base64," + base64.b64encode(buf.getvalue()).decode()


# --- svg ---------------------------------------------------------------------


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shell(width: int, height: int, fonts: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<style>
{fonts}
text {{ font-family: 'Sen'; }}
</style>
{body}
</svg>
"""


def face(weight: int, uri: str) -> str:
    return (
        "@font-face { font-family: 'Sen'; font-style: normal; "
        f"font-weight: {weight}; src: url({uri}) format('woff2'); }}"
    )


def header(c: dict, fonts: str) -> str:
    height = 196
    rows = "".join(
        f'<text x="{W - PAD}" y="{y}" text-anchor="end" font-size="14" '
        f'font-weight="400" fill="{c[tone]}">{esc(value)}</text>'
        for (value, tone), y in zip(META, (66, 94, 122))
    )
    return shell(
        W,
        height,
        fonts,
        f"""<rect x="{PAD}" y="54" width="7" height="7" fill="{c['accent']}"/>
<text x="{PAD + 19}" y="61" font-size="13" font-weight="400" letter-spacing="0.6" fill="{c['muted']}">{esc(HANDLE)}</text>
<text x="{PAD}" y="128" font-size="52" font-weight="700" letter-spacing="-1.4" fill="{c['fg']}">{esc(NAME)}</text>
<text x="{PAD}" y="162" font-size="17" font-weight="400" fill="{c['muted']}">{esc(TAGLINE)}</text>
{rows}""",
    )


def stack(c: dict, fonts: str) -> str:
    row_height, top = 46, 42
    parts = []
    for i, (label, items) in enumerate(STACK):
        y = top + i * row_height
        joined = f'<tspan fill="{c["muted"]}"> · </tspan>'.join(esc(x) for x in items)
        parts.append(
            f'<text x="{PAD}" y="{y}" font-size="12" font-weight="700" '
            f'letter-spacing="1.4" fill="{c["muted"]}">{esc(label)}</text>'
            f'<text x="{PAD + 152}" y="{y}" font-size="16" font-weight="400" fill="{c["fg"]}">{joined}</text>'
        )
        if i < len(STACK) - 1:
            parts.append(
                f'<rect x="{PAD}" y="{y + 16}" width="{W - PAD * 2}" height="1" fill="{c["rule"]}"/>'
            )
    return shell(W, top + len(STACK) * row_height - 24, fonts, "\n".join(parts))


# --- build -------------------------------------------------------------------


def main() -> None:
    glyphs = "".join(
        sorted(
            set(
                NAME
                + HANDLE
                + TAGLINE
                + "".join(v for v, _ in META)
                + "".join(label + "".join(items) for label, items in STACK)
                + " ·"
            )
        )
    )

    fonts = "\n".join(face(w, font_data_uri(w, glyphs)) for w in (400, 700))

    OUT.mkdir(exist_ok=True)
    for theme, colours in THEMES.items():
        for name, render in (("header", header), ("stack", stack)):
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(render(colours, fonts), encoding="utf-8")
            print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    sys.exit(main())
