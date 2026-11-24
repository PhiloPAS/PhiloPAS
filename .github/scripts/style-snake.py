import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


HEAD_COLOR = (134, 239, 172)
TAIL_COLOR = (21, 128, 61)
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
STEP_MS = 100  # Platane/snk v3 advances one cell per 100 ms.


def style_snake(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    style = root.find(f"{{{SVG_NAMESPACE}}}style")
    if style is None or not style.text:
        raise ValueError(f"{path}: expected a Platane SVG stylesheet")
    stylesheet = style.text
    grid_width = re.search(r"\.c\s*\{[^}]*?(?<![\w-])width:\s*([\d.]+)px", stylesheet)

    rectangles = root.findall(f"{{{SVG_NAMESPACE}}}rect")
    origin_cell = next((rect for rect in rectangles if "c" in rect.get("class", "").split()), None)
    segments = [rect for rect in rectangles if "s" in rect.get("class", "").split()]
    if grid_width is None or origin_cell is None or not segments:
        raise ValueError(f"{path}: expected a Platane SVG with grid cells and snake segments")

    size = grid_width.group(1)
    cell_shape = {name: origin_cell.attrib[name] for name in ("x", "y", "rx", "ry")}

    add_growth(root, style, segments)

    # Platane emits the head first, followed by each segment in tail order.
    for index, segment in enumerate(segments):
        progress = index / max(1, len(segments) - 1)
        color = "".join(
            f"{round(start + (end - start) * progress):02x}"
            for start, end in zip(HEAD_COLOR, TAIL_COLOR)
        )
        segment.attrib.update(cell_shape, width=size, height=size)
        declarations = (segment.get("style"), f"fill:#{color}")
        segment.set("style", ";".join(filter(None, declarations)))

    tree.write(path, encoding="utf-8")


def add_growth(root: ET.Element, style: ET.Element, segments: list[ET.Element]) -> None:
    stylesheet = style.text or ""
    # Each cell's animation switches to the empty fill just after the head reaches it.
    eaten_at = sorted(
        re.findall(
            r"@keyframes c[0-9a-z]+\s*\{\s*[\d.]+%\s*\{[^{}]+\}\s*([\d.]+)%",
            stylesheet,
        ),
        key=float,
    )
    if not eaten_at:
        return

    motion_duration = re.search(r"\.s\s*\{[^}]*?animation:[^}]*?\b(\d+)ms\b", stylesheet)
    if motion_duration is None:
        raise ValueError("Expected a Platane animation duration for snake growth")

    duration = motion_duration.group(1)
    tail_animation = segments[-1].attrib["class"].split()[-1]
    growth_rules = []

    # Reuse the tail's route with one more step of delay for each new segment.
    for index, percent in enumerate(eaten_at, start=1):
        visibility = f"grow{index}"
        growth_rules.append(f"@keyframes {visibility}{{0%{{opacity:0}}{percent}%,100%{{opacity:1}}}}")
        segment = ET.SubElement(root, f"{{{SVG_NAMESPACE}}}rect", {"class": "s"})
        segment.set(
            "style",
            f"animation:{tail_animation} {duration}ms linear {index * STEP_MS}ms infinite backwards,"
            f"{visibility} {duration}ms steps(1,end) infinite",
        )
        segments.append(segment)

    style.text = stylesheet + "".join(growth_rules)


if __name__ == "__main__":
    ET.register_namespace("", SVG_NAMESPACE)
    for filename in sys.argv[1:]:
        style_snake(Path(filename))
