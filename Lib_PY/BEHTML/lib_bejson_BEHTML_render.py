"""
Library:         lib_bejson_BEHTML_render.py
Family:          BEHTML
Module Purpose:  Minimal Tri-Color HTML5 renderer for BEHTML 105 documents (8-lane X, Ry=32px Y, Rz=32px Z).
Architecture:    BEHTML on BEJSON 105: one 105 table, one row per placed element, X0-X7 lanes, Ry=32px rows, Rz=32px layers; all field access via the Core field map.
Version:         1.0.0
Release_Version: 301
Date:            2026-11-16
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   7c8a4b9e-2d13-4f88-a05b-1d2e3f4a5b6c
"""

import html
from typing import Any, Dict, List, Optional

import lib_bejson_BEHTML_bootstrap  # noqa: F401 -- puts 105 Core on sys.path

from lib_bejson_BEHTML_bejson_errors import E_BEHTML_RENDER_FAILED
from lib_bejson_BEHTML_core import (
    BEHTML_COLOR_ACCENT,
    BEHTML_COLOR_BLACK,
    BEHTML_COLOR_WHITE,
    BEHTMLError,
    ZPolicy,
    behtml_core_grid_cell_classes,
    behtml_core_row_to_dict,
    behtml_core_x_span_to_percent,
    behtml_core_y_span_to_px,
    behtml_core_z_css,
    behtml_core_z_depth_px,
)
from lib_bejson_BEHTML_validator import behtml_validator_validate_document

VERSION = "1.0.0"

_SEMANTIC_TAGS = {
    "header": "header",
    "footer": "footer",
    "sidebar": "aside",
    "section": "section",
    "button": "button",
    "link": "a",
    "label": "label",
    "table": "table",
    "image": "img",
}


def behtml_render_element_html(el: Dict[str, Any], children_html: str = "") -> str:
    """Render one BEHTMLElement dict to deterministic positioned HTML."""
    eid = html.escape(str(el.get("element_id") or ""))
    etype = str(el.get("element_type") or "div")
    tag = _SEMANTIC_TAGS.get(etype, "div")
    classes = behtml_core_grid_cell_classes(
        el["x_start"], el["x_span"], el["y_span"], active=bool(el.get("is_active"))
    )
    classes.append(f"behtml-el--{html.escape(etype)}")
    left_pct = behtml_core_x_span_to_percent(el["x_start"]) if el["x_start"] else 0.0
    width_pct = behtml_core_x_span_to_percent(el["x_span"])
    top_px = el["y_start"] * 32
    height_px = behtml_core_y_span_to_px(el["y_span"])
    z_css = behtml_core_z_css(el["z_layer"], el["z_half"])
    style = (
        f"position:absolute;left:{left_pct}%;width:{width_pct}%;"
        f"top:{top_px}px;height:{height_px}px;{z_css}"
    )
    content = html.escape(str(el.get("content_ref") or ""))
    if tag == "img":
        return f'<img id="{eid}" class="{" ".join(classes)}" src="{content}" alt="{eid}" style="{style}" />'
    attrs = f'id="{eid}" class="{" ".join(classes)}" data-z="{el["z_layer"]}" style="{style}"'
    if tag == "a":
        attrs += f' href="{content or "#"}"'
    return f"<{tag} {attrs}>{content}{children_html}</{tag}>"


def behtml_render_document_html(doc: Dict[str, Any], title: str = "BEHTML Document",
                                policy: Optional[ZPolicy] = None) -> str:
    """Validate and render a BEHTML 105 document into a standalone Tri-Color HTML5 page."""
    try:
        behtml_validator_validate_document(doc, policy=policy)
        elements = [behtml_core_row_to_dict(doc, row) for row in doc.get("Values", [])]
    except BEHTMLError:
        raise
    except Exception as exc:
        raise BEHTMLError(E_BEHTML_RENDER_FAILED, f"render failed: {exc}") from exc

    by_parent: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for el in elements:
        by_parent.setdefault(el.get("parent_id_fk"), []).append(el)

    def render_branch(parent_id: Optional[str]) -> str:
        items = sorted(
            by_parent.get(parent_id, []),
            key=lambda e: (behtml_core_z_depth_px(e["z_layer"], e["z_half"]), e["y_start"], e["x_start"]),
        )
        return "\n".join(behtml_render_element_html(item, render_branch(item["element_id"])) for item in items)

    body_html = render_branch(None)
    safe_title = html.escape(title)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />\n"
        f"<title>{safe_title}</title>\n<style>\n"
        f"body{{margin:0;background:{BEHTML_COLOR_BLACK};color:{BEHTML_COLOR_WHITE};font-family:monospace;}}\n"
        ".behtml-stage{position:relative;width:100vw;min-height:100vh;overflow-x:hidden;}\n"
        f".behtml-el--scrim{{background:rgba(0,0,0,0.72);}}\n"
        f".behtml-el--button{{background:{BEHTML_COLOR_ACCENT};color:{BEHTML_COLOR_WHITE};border:none;}}\n"
        "</style>\n</head>\n<body>\n"
        f"<main class=\"behtml-stage\">\n{body_html}\n</main>\n"
        "</body>\n</html>\n"
    )
