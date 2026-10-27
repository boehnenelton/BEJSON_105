"""
Package:        Lib_PY/Canvas
Family:         Canvas
Description:    BEJSON 105 Canvas Templates and SVG Animation Studio Library Family.
Version:        1.0.0
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
"""

from .lib_bejson_Canvas_canvas_schemas import (
    CANVAS_STUDIO_CONFIG_FIELDS,
    CANVAS_FRAME_SEQUENCE_FIELDS,
    build_field_map_105,
    create_canvas_config_105a,
    create_frame_sequence_105a,
    compute_frame_seek_points,
    validate_canvas_config,
    get_config_dict
)

from .lib_bejson_Canvas_canvas_templates import (
    CANVAS_TEMPLATE_CATALOG,
    resolve_template_root,
    list_canvas_templates,
    get_template_path,
    load_template,
    render_canvas_html,
    instantiate_stage_html
)

__all__ = [
    "CANVAS_STUDIO_CONFIG_FIELDS",
    "CANVAS_FRAME_SEQUENCE_FIELDS",
    "build_field_map_105",
    "create_canvas_config_105a",
    "create_frame_sequence_105a",
    "compute_frame_seek_points",
    "validate_canvas_config",
    "get_config_dict",
    "CANVAS_TEMPLATE_CATALOG",
    "resolve_template_root",
    "list_canvas_templates",
    "get_template_path",
    "load_template",
    "render_canvas_html",
    "instantiate_stage_html"
]
