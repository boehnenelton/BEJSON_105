"""
Package:        Lib_PY.Graphics
Description:    Elton Boehnen's BEJSON 105a Graphics Library Family.
                Provides blank-slate canvas stages, dynamic frame Playwright capture,
                FPS and timeline pacing declarations, row-per-frame animation ledgers,
                slideshow generation, and multi-format GIF/WebM/APNG/MP4 export engines.
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Version:        1.0.0
Date:           2026-10-27
"""

from .lib_bejson_Graphics_graphics_schemas import (
    GRAPHIC_CANVAS_CONFIG_FIELDS,
    GRAPHIC_ROW_FRAME_FIELDS,
    GRAPHIC_TEMPLATE_REGISTRY_FIELDS,
    build_field_map_105,
    create_graphic_stage_config_105a,
    create_row_per_frame_animation_105a,
    create_slideshow_animation_105a,
    validate_graphic_105a_doc,
)

from .lib_bejson_Graphics_graphics_canvas_templates import (
    BLANK_SLATE_ARCHETYPES,
    generate_blank_slate_html,
    get_canvas_template_registry_105a,
    get_template_html,
    instantiate_stage_file,
    list_registered_templates,
)

from .lib_bejson_Graphics_graphics_core import (
    compile_frames_to_apng,
    compile_frames_to_gif,
    compile_frames_to_mp4,
    compile_frames_to_webm,
    compile_row_per_frame_to_animated_svg,
    create_isometric_cube_svg,
    render_row_per_frame_animation,
    render_still_frame,
)

from .lib_bejson_Graphics_graphics_diagram_loader import (
    calculate_diagram_bounds,
    compute_fit_viewport,
    compute_shape_focus_viewport,
    create_diagram_frame_sequence_105a,
    render_diagram_svg,
)

__all__ = [
    "GRAPHIC_CANVAS_CONFIG_FIELDS",
    "GRAPHIC_ROW_FRAME_FIELDS",
    "GRAPHIC_TEMPLATE_REGISTRY_FIELDS",
    "build_field_map_105",
    "create_graphic_stage_config_105a",
    "create_row_per_frame_animation_105a",
    "create_slideshow_animation_105a",
    "validate_graphic_105a_doc",
    "BLANK_SLATE_ARCHETYPES",
    "generate_blank_slate_html",
    "get_canvas_template_registry_105a",
    "get_template_html",
    "instantiate_stage_file",
    "list_registered_templates",
    "compile_frames_to_apng",
    "compile_frames_to_gif",
    "compile_frames_to_mp4",
    "compile_frames_to_webm",
    "compile_row_per_frame_to_animated_svg",
    "create_isometric_cube_svg",
    "render_row_per_frame_animation",
    "render_still_frame",
    "calculate_diagram_bounds",
    "compute_fit_viewport",
    "compute_shape_focus_viewport",
    "create_diagram_frame_sequence_105a",
    "render_diagram_svg",
]

