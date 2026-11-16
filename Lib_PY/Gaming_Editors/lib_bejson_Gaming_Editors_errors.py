"""
Library:        lib_bejson_Gaming_Editors_errors.py
Family:         Gaming_Editors
Description:    Unified error registry for Gaming_Editors 105 Family (520-539).
                Defines numeric error codes for Game Editors (Sprite Studio,
                Tilemap Palette Studio, HUD Stage Studio, and Animation Studio).
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
                (Pronounced Bee-Jay-Son / Bay-nin Elton JSON)
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-11-15
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:        PolyForm-Noncommercial-1.0.0
RELATIONAL_ID:  7b9a1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d
Release_Version: 300

Range claim: 520-539. Checked against libraries_104 + libraries_105:
Core 1-99 (MD 90-99), Core_Nesting 130-159, Core_Extension 160-189, AI 200-235,
Standards 250-269, Cognition 270-289, BEHTML 300-329, BEHTML_IDE 330-359,
Terminal_Menus 360-389, Job 390-419, Diagrams 420-449, Bookmaker 450-479,
Lists 480-499, Graphics 500-519: no overlap.
"""

from __future__ import annotations

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Gaming_Editors Domain Error Codes (520-539)
# ---------------------------------------------------------------------------
E_GAMING_EDITORS_CORE_VALIDATION_FAILED     = 520  # Core Family validator failed; barrier of entry rejected editor document
E_GAMING_EDITORS_INVALID_RECORDS_TYPE       = 521  # Records_Type is not a recognized Gaming_Editors record type
E_GAMING_EDITORS_INVALID_SPRITE_GRID        = 522  # Cell dimensions, rows, cols or cell size invalid (must be 16, 32, 48, 64)
E_GAMING_EDITORS_INVALID_TILEMAP_PALETTE    = 523  # Tile dimensions or autotile matrix bounds invalid
E_GAMING_EDITORS_INVALID_COLLISION_FLAG     = 524  # Tile collision flag invalid (must be 0/pass or 1/solid)
E_GAMING_EDITORS_INVALID_HUD_LAYOUT         = 525  # HUD gauge, slot or container definition malformed
E_GAMING_EDITORS_INVALID_ANIM_TIMELINE      = 526  # Animation frame count < 1 or timeline frame durations malformed
E_GAMING_EDITORS_INVALID_SVG_MARKUP         = 527  # Injected SVG markup is invalid or unclosed
E_GAMING_EDITORS_PALETTE_VIOLATION          = 528  # Color value deviates from authorized palette standards
E_GAMING_EDITORS_STAGE_NOT_FOUND            = 529  # Target HTML stage template file not found on disk
E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED    = 530  # Compound barrier failure: document failed either Core or Gaming_Editors gate
# 531-539 reserved, unassigned.

ERROR_NAMES = {
    520: "E_GAMING_EDITORS_CORE_VALIDATION_FAILED",
    521: "E_GAMING_EDITORS_INVALID_RECORDS_TYPE",
    522: "E_GAMING_EDITORS_INVALID_SPRITE_GRID",
    523: "E_GAMING_EDITORS_INVALID_TILEMAP_PALETTE",
    524: "E_GAMING_EDITORS_INVALID_COLLISION_FLAG",
    525: "E_GAMING_EDITORS_INVALID_HUD_LAYOUT",
    526: "E_GAMING_EDITORS_INVALID_ANIM_TIMELINE",
    527: "E_GAMING_EDITORS_INVALID_SVG_MARKUP",
    528: "E_GAMING_EDITORS_PALETTE_VIOLATION",
    529: "E_GAMING_EDITORS_STAGE_NOT_FOUND",
    530: "E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED",
}


class GamingEditorsValidationError(Exception):
    """Raised when an editor document fails Gaming_Editors validation or Core barrier of entry."""

    def __init__(self, message: str, code: int = E_GAMING_EDITORS_BARRIER_OF_ENTRY_FAILED):
        error_name = ERROR_NAMES.get(code, f"E_GAMING_EDITORS_{code}")
        super().__init__(f"[{error_name}] {message}")
        self.code = code
        self.message = message
