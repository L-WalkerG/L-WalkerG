"""Generate a continuous, in-grid contribution snake using only Python's stdlib."""

import json
import os
from pathlib import Path
import urllib.request


def route(width, height=7):
    # Reserve the top row for the return journey; every turn stays on the grid.
    if width < 2 or width % 2 or height < 2:
        raise ValueError("The loop requires an even width and at least two rows")
    points = [(x, 0) for x in range(width)]
    for x in reversed(range(width)):
        rows = range(1, height) if x % 2 else range(height - 1, 0, -1)
        points.extend((x, y) for y in rows)
    return points


def render(weeks, dark=False):
    width = len(weeks) + len(weeks) % 2
    points = route(width)
    indices = {point: i for i, point in enumerate(points)}
    count = len(points)
    duration = count * 0.11
    palette = (["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
               if dark else ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"])
    levels = {name: i for i, name in enumerate([
        "NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"
    ])}
    cells = {(x, y): 0 for x in range(width) for y in range(7)}
    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:
            cells[x, day["weekday"]] = levels[day["contributionLevel"]]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 16 + 16}" '
           f'height="128" viewBox="-8 -8 {width * 16 + 16} 128" role="img">',
           '<title>Contribution snake</title>',
           '<desc>A snake follows a continuous zigzag loop inside the contribution grid.</desc>']
    for (x, y), level in cells.items():
        color = palette[level]
        svg.append(f'<rect x="{x * 16 + 2}" y="{y * 16 + 2}" width="12" height="12" rx="3" fill="{color}">')
        if level:
            # Each food cell regrows before the next visit, without a pile below.
            delay = indices[x, y] * 0.11
            svg.append(f'<animate attributeName="fill" values="{palette[0]};{palette[0]};{color};{color}" '
                       f'keyTimes="0;0.65;0.72;1" begin="{delay:.2f}s" dur="{duration:.2f}s" repeatCount="indefinite"/>')
        svg.append('</rect>')
    for segment in reversed(range(6)):
        positions = [points[(i - segment) % count] for i in range(count + 1)]
        values = ";".join(f"{x * 16},{y * 16}" for x, y in positions)
        color = ("#f5c542" if segment == 0 else "#d99b25") if dark else ("#8250df" if segment == 0 else "#a475ed")
        svg.append(f'<g><animateTransform attributeName="transform" type="translate" values="{values}" '
                   f'dur="{duration:.2f}s" repeatCount="indefinite" calcMode="linear"/>')
        svg.append(f'<rect x="1" y="1" width="14" height="14" rx="5" fill="{color}"/>')
        if segment == 0:
            svg.append('<circle cx="5" cy="5" r="1.5" fill="#fff"/><circle cx="10" cy="5" r="1.5" fill="#fff"/>')
        svg.append('</g>')
    svg.append('</svg>')
    return "".join(svg)


def main():
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{weeks{contributionDays{weekday contributionLevel}}}
    }}}"""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": os.environ["GITHUB_USER"]}}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json", "User-Agent": "contribution-snake"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    if not weeks:
        raise ValueError("GitHub returned no contribution weeks")
    Path("dist").mkdir(exist_ok=True)
    for dark in (False, True):
        suffix = "-dark" if dark else ""
        Path(f"dist/github-contribution-grid-snake{suffix}.svg").write_text(render(weeks, dark))


if __name__ == "__main__":
    main()
