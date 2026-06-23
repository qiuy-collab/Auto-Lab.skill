import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = (1600, 1000)
BG = "white"
TEXT = "#0f172a"
LINE = "#334155"
BOX = "#f8fafc"
HILITE = "#dbeafe"
STORE = "#e2e8f0"
TITLE = "#111827"
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate diagram assets for auto-lab.")
    parser.add_argument("--workflow", required=True, help="Path to workflow.json")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def get_font(size: int, bold: bool = False):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    if not text:
        return [""]
    tokens = text.split(" ")
    if len(tokens) == 1:
        tokens = list(text)
    lines = []
    current = ""
    for token in tokens:
        proposal = token if not current else f"{current} {token}" if " " in text else current + token
        bbox = draw.textbbox((0, 0), proposal, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = proposal
        else:
            lines.append(current)
            current = token
    if current:
        lines.append(current)
    return lines


def fit_text(draw, text, max_width, max_height, start_size=30, min_size=14, bold=False):
    for size in range(start_size, min_size - 1, -2):
        font = get_font(size, bold=bold)
        lines = wrap_text(draw, text, font, max_width)
        line_height = int(size * 1.35)
        total_height = len(lines) * line_height
        max_line = max((draw.textbbox((0, 0), line, font=font)[2] for line in lines), default=0)
        if max_line <= max_width and total_height <= max_height:
            return font, lines, line_height
    font = get_font(min_size, bold=bold)
    lines = wrap_text(draw, text, font, max_width)
    return font, lines, int(min_size * 1.35)


def draw_multiline_center(draw, rect, text, fill=TEXT, bold=False):
    x1, y1, x2, y2 = rect
    font, lines, line_height = fit_text(draw, text, x2 - x1 - 30, y2 - y1 - 20, bold=bold)
    total_height = len(lines) * line_height
    y = (y1 + y2 - total_height) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (x1 + x2 - line_width) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def draw_title(draw, title):
    font = get_font(30, bold=True)
    bbox = draw.textbbox((0, 0), title, font=font)
    x = (CANVAS_SIZE[0] - (bbox[2] - bbox[0])) / 2
    draw.text((x, 34), title, font=font, fill=TITLE)


def rounded_box(draw, rect, fill=BOX):
    draw.rounded_rectangle(rect, radius=20, outline=LINE, fill=fill, width=3)


def draw_box(draw, rect, text, fill=BOX):
    rounded_box(draw, rect, fill=fill)
    draw_multiline_center(draw, rect, text)


def draw_diamond(draw, rect, text):
    x1, y1, x2, y2 = rect
    points = [((x1 + x2) / 2, y1), (x2, (y1 + y2) / 2), ((x1 + x2) / 2, y2), (x1, (y1 + y2) / 2)]
    draw.polygon(points, outline=LINE, fill=BOX)
    draw_multiline_center(draw, rect, text)


def draw_ellipse(draw, rect, text, fill=HILITE):
    draw.ellipse(rect, outline=LINE, fill=fill, width=3)
    draw_multiline_center(draw, rect, text)


def draw_data_store(draw, rect, text):
    x1, y1, x2, y2 = rect
    draw.rectangle(rect, outline=LINE, fill=STORE, width=3)
    draw.line([(x1 + 18, y1), (x1 + 18, y2)], fill=LINE, width=3)
    draw_multiline_center(draw, rect, text)


def label_text(draw, point, text):
    font = get_font(18)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = point[0] - (bbox[2] - bbox[0]) / 2
    y = point[1] - (bbox[3] - bbox[1]) / 2
    draw.rounded_rectangle((x - 8, y - 4, x + (bbox[2] - bbox[0]) + 8, y + (bbox[3] - bbox[1]) + 4), radius=8, fill="white")
    draw.text((x, y), text, font=font, fill=TEXT)


def arrow_head(draw, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    mag = max((dx * dx + dy * dy) ** 0.5, 1)
    ux = dx / mag
    uy = dy / mag
    left = (end[0] - 18 * ux - 7 * uy, end[1] - 18 * uy + 7 * ux)
    right = (end[0] - 18 * ux + 7 * uy, end[1] - 18 * uy - 7 * ux)
    draw.polygon([end, left, right], fill=LINE)


def draw_poly_arrow(draw, points, label=None, label_point=None, draw_arrow=True):
    if len(points) < 2:
        raise SystemExit("Each diagram edge path must contain at least two points")
    for a, b in zip(points, points[1:]):
        if a == b:
            raise SystemExit("Diagram edge path contains duplicate adjacent points")
        draw.line([a, b], fill=LINE, width=4)
    if draw_arrow:
        arrow_head(draw, points[-2], points[-1])
    if label:
        if label_point is None:
            mid = points[len(points) // 2]
            label_point = (mid[0], mid[1] - 18)
        label_text(draw, tuple(label_point), label)


def point(rect, anchor):
    x1, y1, x2, y2 = rect
    mapping = {
        "top": ((x1 + x2) / 2, y1),
        "bottom": ((x1 + x2) / 2, y2),
        "left": (x1, (y1 + y2) / 2),
        "right": (x2, (y1 + y2) / 2),
        "center": ((x1 + x2) / 2, (y1 + y2) / 2),
    }
    return mapping[anchor]


def edge_points(edge, nodes):
    if "path" in edge:
        return [tuple(p) for p in edge["path"]]
    start_rect = nodes[edge["from"]]
    end_rect = nodes[edge["to"]]
    start = point(start_rect, edge.get("from_anchor", "bottom"))
    end = point(end_rect, edge.get("to_anchor", "top"))
    route = edge.get("route", "vh")
    if route == "straight":
        return [start, end]
    if route == "hv":
        return [start, (end[0], start[1]), end]
    return [start, (start[0], end[1]), end]


def render_function_diagram(diagram, output_path: Path):
    image = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw_title(draw, diagram["title"])
    nodes = {node["id"]: node["rect"] for node in diagram["nodes"]}
    for node in diagram["nodes"]:
        draw_box(draw, node["rect"], node["label"], HILITE if node.get("primary") else BOX)
    for edge in diagram.get("edges", []):
        draw_poly_arrow(draw, edge_points(edge, nodes), edge.get("label"), edge.get("label_point"), edge.get("arrow", True))
    image.save(output_path)


def render_flow_diagram(diagram, output_path: Path):
    image = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw_title(draw, diagram["title"])
    nodes = {node["id"]: node["rect"] for node in diagram["nodes"]}
    for node in diagram["nodes"]:
        if node.get("shape") == "diamond":
            draw_diamond(draw, node["rect"], node["label"])
        else:
            draw_box(draw, node["rect"], node["label"])
    for edge in diagram.get("edges", []):
        draw_poly_arrow(draw, edge_points(edge, nodes), edge.get("label"), edge.get("label_point"), edge.get("arrow", True))
    image.save(output_path)


def render_dfd(diagram, output_path: Path):
    image = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw_title(draw, diagram["title"])
    nodes = {}
    for process in diagram.get("processes", []):
        nodes[process["id"]] = process["rect"]
        draw_ellipse(draw, process["rect"], process["label"])
    for store in diagram.get("stores", []):
        nodes[store["id"]] = store["rect"]
        draw_data_store(draw, store["rect"], store["label"])
    for entity in diagram.get("entities", []):
        nodes[entity["id"]] = entity["rect"]
        draw_box(draw, entity["rect"], entity["label"])
    for flow in diagram.get("flows", []):
        draw_poly_arrow(draw, edge_points(flow, nodes), flow.get("label"), flow.get("label_point"), flow.get("arrow", True))
    image.save(output_path)


def render_er(diagram, output_path: Path):
    image = Image.new("RGB", CANVAS_SIZE, BG)
    draw = ImageDraw.Draw(image)
    draw_title(draw, diagram["title"])
    nodes = {}
    for entity in diagram.get("entities", []):
        nodes[entity["id"]] = entity["rect"]
        draw_box(draw, entity["rect"], entity["label"], HILITE)
        attr_y = entity["rect"][3] + 26
        for attr in entity.get("attributes", []):
            attr_width = entity.get("attribute_width", 220)
            attr_x = entity["rect"][0] + ((entity["rect"][2] - entity["rect"][0]) - attr_width) / 2
            rect = [attr_x, attr_y, attr_x + attr_width, attr_y + 44]
            draw.ellipse(rect, outline=LINE, fill="white", width=2)
            draw_multiline_center(draw, rect, attr)
            attr_y += 56
    for relation in diagram.get("relations", []):
        nodes[relation["id"]] = relation["rect"]
        draw_diamond(draw, relation["rect"], relation["label"])
    for edge in diagram.get("edges", []):
        draw_poly_arrow(draw, edge_points(edge, nodes), edge.get("label"), edge.get("label_point"), edge.get("arrow", True))
    image.save(output_path)


def render_diagram(diagram, output_path: Path):
    kind = diagram["kind"]
    if kind == "function_diagram":
        render_function_diagram(diagram, output_path)
    elif kind == "flowchart":
        render_flow_diagram(diagram, output_path)
    elif kind == "data_flow_diagram":
        render_dfd(diagram, output_path)
    elif kind == "er_diagram":
        render_er(diagram, output_path)
    else:
        raise SystemExit(f"Unsupported diagram kind: {kind}")


def main():
    args = parse_args()
    workflow = load_json(Path(args.workflow).expanduser().resolve())
    diagram_plan_path = Path(workflow["diagram_plan_path"])
    diagram_plan = load_json(diagram_plan_path)
    output_dir = Path(workflow["images_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not diagram_plan.get("enabled", False):
        raise SystemExit("diagram_plan.json is not enabled")

    for diagram in diagram_plan.get("diagrams", []):
        target = output_dir / f"{diagram['name']}.png"
        render_diagram(diagram, target)
        print(f"Generated diagram asset: {target}")


if __name__ == "__main__":
    main()
