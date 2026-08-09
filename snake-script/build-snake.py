"""Renders the contribution-graph snake as a self-contained animated SVG.

The usual way to get this is Platane/snk running as a GitHub Action, which is
not an option while Actions is locked. The contribution grid is public HTML, so
the whole thing can be built locally and committed:

    python scripts/build-snake.py

Re-run it whenever the graph should catch up. Nothing here needs a token — the
page it reads is the same one anyone sees on the profile.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
USER = "Takayashii"

PITCH = 14
DOT = 11
PAD = 8
ROWS = 7
DURATION = 22.0
TRAIL = 5

THEMES = {
    "dark": {
        "empty": "#161b22",
        "levels": ["#161b22", "#0a273d", "#10477a", "#0057bb", "#3f8af4"],
        "snake": "#2482e0",
    },
    "light": {
        "empty": "#ebedf0",
        "levels": ["#ebedf0", "#cfe4f7", "#91c2e7", "#3a8bc9", "#006dbb"],
        "snake": "#0600bb",
    },
}


def fetch_grid() -> dict[tuple[int, int], int]:
    """Returns {(col, row): level} from the public contributions fragment."""
    html = subprocess.run(
        ["curl", "-sL", f"https://github.com/users/{USER}/contributions"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout

    cells = {}
    for match in re.finditer(r'id="contribution-day-component-(\d+)-(\d+)"[^>]*data-level="(\d)"', html):
        row, col, level = (int(g) for g in match.groups())
        cells[(col, row)] = level

    if not cells:
        sys.exit("Contribution grid could not be read — GitHub's HTML may have changed.")
    return cells


def path_steps(cols: int) -> list[tuple[int, int]]:
    """Boustrophedon sweep: down one column, up the next, so every cell is visited."""
    steps = []
    for col in range(cols):
        rows = range(ROWS) if col % 2 == 0 else reversed(range(ROWS))
        steps.extend((col, row) for row in rows)
    return steps


def render(cells: dict[tuple[int, int], int], theme: dict) -> str:
    cols = max(col for col, _ in cells) + 1
    steps = path_steps(cols)
    total = len(steps)

    width = PAD * 2 + cols * PITCH
    height = PAD * 2 + ROWS * PITCH - (PITCH - DOT)

    eaten_at = {cell: i for i, cell in enumerate(steps)}

    rects, keyframes = [], []
    for (col, row), level in sorted(cells.items()):
        x, y = PAD + col * PITCH, PAD + row * PITCH
        if level == 0:
            rects.append(
                f'<rect x="{x}" y="{y}" width="{DOT}" height="{DOT}" rx="2" fill="{theme["empty"]}"/>'
            )
            continue

        name = f"e{col}_{row}"
        at = eaten_at[(col, row)] / total * 100
        gone = min(at + 0.35, 100)
        keyframes.append(
            f"@keyframes {name}{{0%,{at:.2f}%{{fill:{theme['levels'][level]}}}"
            f"{gone:.2f}%,100%{{fill:{theme['empty']}}}}}"
        )
        rects.append(
            f'<rect x="{x}" y="{y}" width="{DOT}" height="{DOT}" rx="2" '
            f'fill="{theme["levels"][level]}" style="animation:{name} {DURATION}s linear infinite"/>'
        )

    # One path animation, reused by every segment. Each trailing segment seeks
    # into it with a negative delay instead of carrying its own copy.
    stops = []
    for i, (col, row) in enumerate(steps):
        stops.append(
            f"{i / total * 100:.3f}%{{transform:translate({PAD + col * PITCH}px,{PAD + row * PITCH}px)}}"
        )
    stops.append(f"100%{{transform:translate({PAD}px,{PAD}px)}}")
    keyframes.append("@keyframes crawl{" + "".join(stops) + "}")

    step_time = DURATION / total
    segments = []
    for k in range(TRAIL):
        # Same size for every segment — an SVG rect ignores margin, so a smaller
        # tail would sit off-centre rather than tucked inside the cell.
        opacity = 1 - k * 0.16
        segments.append(
            f'<rect width="{DOT}" height="{DOT}" rx="3" fill="{theme["snake"]}" opacity="{opacity:.2f}" '
            f'style="animation:crawl {DURATION}s linear infinite;'
            f"animation-delay:{-(DURATION - k * step_time):.3f}s;"
            f'transform:translate({PAD}px,{PAD}px)"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        f"<style>{''.join(keyframes)}</style>\n"
        + "\n".join(rects)
        + "\n"
        + "\n".join(segments)
        + "\n</svg>\n"
    )


def main() -> None:
    cells = fetch_grid()
    filled = sum(1 for v in cells.values() if v)
    print(f"{len(cells)} gün, {filled} tanesi dolu")

    OUT.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        path = OUT / f"snake-{name}.svg"
        path.write_text(render(cells, theme), encoding="utf-8")
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
