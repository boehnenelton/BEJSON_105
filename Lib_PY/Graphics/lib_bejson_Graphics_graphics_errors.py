"""
Library:        lib_bejson_Graphics_graphics_errors.py
Family:         Graphics
Description:    Unified error registry for Graphics Domain (500-519).
                Defines numeric error codes for blank-slate canvas stages,
                timeline schemas, frame duration quantization, and procedural renderers.
Version:        1.1.0
Date:           2026-11-01
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  9a5e8c1b-7d2f-4e0a-b3c4-1d2e3f4a5b6c
Release_Version: 300

Range claim: 500-519. Checked against libraries_104 + libraries_105:
Core 1-99 (MD 90-99), Core_Nesting 130-159, Core_Extension 160-189, AI 200-235,
Standards 250-269, Cognition 270-289, BEHTML 300-329, BEHTML_IDE 330-359,
Terminal_Menus 360-389, Diagrams 420-449, Bookmaker 450-479, Lists 480-499: no overlap.
"""

from __future__ import annotations

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Graphics Domain Error Codes (500-519)
# ---------------------------------------------------------------------------
E_GRAPHICS_CORE_VALIDATION_FAILED    = 500  # Core Family validator failed; foundational barrier of entry rejected document
E_GRAPHICS_INVALID_RECORDS_TYPE      = 501  # Records_Type is not a recognized Graphics record type
E_GRAPHICS_INVALID_DIMENSIONS        = 502  # Width_Px or Height_Px missing, <= 0, or not integer
E_GRAPHICS_INVALID_ASPECT_RATIO      = 503  # Aspect_Ratio format invalid or does not match width:height
E_GRAPHICS_INVALID_FPS               = 504  # FPS missing, <= 0, or non-integer in animation document
E_GRAPHICS_INVALID_DURATION          = 505  # Duration_Sec or frame_duration_ms missing, <= 0
E_GRAPHICS_INVALID_FRAME_SEQUENCE    = 506  # frame_index out of sequence, non-monotonic, or duplicate frame indices
E_GRAPHICS_INVALID_TIMELINE_ROW      = 507  # seek_progress, rotation_deg, scale_factor, or opacity out of bounds
E_GRAPHICS_INVALID_SVG_MARKUP        = 508  # svg_markup empty, not string, or missing valid <svg> / </svg> tags
E_GRAPHICS_PALETTE_VIOLATION         = 509  # Color value violates Policy §8.1 Tri-Color Palette (#000000, #FFFFFF, #DE2626)
E_GRAPHICS_STAGE_CONFIG_INVALID      = 510  # GraphicStageConfig or canvas configuration invalid
E_GRAPHICS_TEMPLATE_NOT_FOUND        = 511  # Referenced canvas HTML template does not exist
E_GRAPHICS_BARRIER_OF_ENTRY_FAILED   = 512  # Compound barrier failure: document failed either Core or Graphics validation gates
# 513-519 reserved, unassigned.

ERROR_NAMES = {
    500: "E_GRAPHICS_CORE_VALIDATION_FAILED",
    501: "E_GRAPHICS_INVALID_RECORDS_TYPE",
    502: "E_GRAPHICS_INVALID_DIMENSIONS",
    503: "E_GRAPHICS_INVALID_ASPECT_RATIO",
    504: "E_GRAPHICS_INVALID_FPS",
    505: "E_GRAPHICS_INVALID_DURATION",
    506: "E_GRAPHICS_INVALID_FRAME_SEQUENCE",
    507: "E_GRAPHICS_INVALID_TIMELINE_ROW",
    508: "E_GRAPHICS_INVALID_SVG_MARKUP",
    509: "E_GRAPHICS_PALETTE_VIOLATION",
    510: "E_GRAPHICS_STAGE_CONFIG_INVALID",
    511: "E_GRAPHICS_TEMPLATE_NOT_FOUND",
    512: "E_GRAPHICS_BARRIER_OF_ENTRY_FAILED",
}


class GraphicsValidationError(Exception):
    """Raised when a graphics document fails Graphics validation or Core barrier of entry."""

    def __init__(self, message: str, code: int = E_GRAPHICS_BARRIER_OF_ENTRY_FAILED):
        error_name = ERROR_NAMES.get(code, f"E_GRAPHICS_{code}")
        super().__init__(f"[{error_name}] {message}")
        self.code = code
        self.message = message
