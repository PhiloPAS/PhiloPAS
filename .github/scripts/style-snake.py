import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


HEAD_COLOR = (134, 239, 172)
TAIL_COLOR = (21, 128, 61)
SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def style_snake(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    stylesheet = root.findtext(f"{{{SVG_NAMESPACE}}}style", default="")
    grid_width = re.search(r"\.c\s*\{[^}]*?(?<![\w-])width:\s*([\d.]+)px", stylesheet)

    rectangles = root.findall(f"{{{SVG_NAMESPACE}}}rect")
    origin_cell = next((rect for rect in rectangles if "c" in rect.get("class", "").split()), None)
    segments = [rect for rect in rectangles if "s" in rect.get("class", "").split()]
    if grid_width is None or origin_cell is None or not segments:
        raise ValueError(f"{path}: expected a Platane SVG with grid cells and snake segments")

    size = grid_width.group(1)
    cell_shape = {name: origin_cell.attrib[name] for name in ("x", "y", "rx", "ry")}

    # Platane emits the head first, followed by each segment in tail order.
    for index, segment in enumerate(segments):
        progress = index / max(1, len(segments) - 1)
        color = "".join(
            f"{round(start + (end - start) * progress):02x}"
            for start, end in zip(HEAD_COLOR, TAIL_COLOR)
        )
        segment.attrib.update(cell_shape, width=size, height=size, style=f"fill:#{color}")

    tree.write(path, encoding="utf-8")


if __name__ == "__main__":
    ET.register_namespace("", SVG_NAMESPACE)
    for filename in sys.argv[1:]:
        style_snake(Path(filename))
