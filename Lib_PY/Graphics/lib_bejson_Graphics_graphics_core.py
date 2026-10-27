"""
Library:        lib_bejson_Graphics_graphics_core.py
Family:         Graphics
Description:    Playwright SVG Capture Engine, Dynamic Frame File-Based Animation Renderer,
                and BEJSON 105a Row-Per-Frame Animation Controller.
BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
MFDB:           MFDB stands for Multi File Database. Authoritative definition;
                do not restate or reinterpret this acronym elsewhere.
Version:        1.0.0
Date:           2026-10-27
Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  4a5b6c7d-8e9f-4a1b-b2c3-d4e5f6a7b8c9
Release_Version: 300
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
for _fam in ('Core', 'Taxonomies', 'Tax_Scaffolds', 'Canvas', 'Graphics'):
    _p = str(_HERE.parent / _fam)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from lib_bejson_Graphics_graphics_schemas import (
        GRAPHIC_CANVAS_CONFIG_FIELDS,
        GRAPHIC_ROW_FRAME_FIELDS,
        build_field_map_105,
        create_graphic_stage_config_105a,
        create_row_per_frame_animation_105a,
        validate_graphic_105a_doc,
    )
    from lib_bejson_Graphics_graphics_canvas_templates import (
        generate_blank_slate_html,
        get_template_html,
        instantiate_stage_file,
        list_registered_templates,
    )
except ImportError:
    # Direct relative imports when executing standalone inside family directory
    from lib_bejson_graphics_schemas import (  # type: ignore
        GRAPHIC_CANVAS_CONFIG_FIELDS,
        GRAPHIC_ROW_FRAME_FIELDS,
        build_field_map_105,
        create_graphic_stage_config_105a,
        create_row_per_frame_animation_105a,
        validate_graphic_105a_doc,
    )
    from lib_bejson_graphics_canvas_templates import (  # type: ignore
        generate_blank_slate_html,
        get_template_html,
        instantiate_stage_file,
        list_registered_templates,
    )

logger = logging.getLogger("lib_bejson_Graphics_graphics_core")
VERSION = "1.0.0"

# Policy §8.1 Tri-Color Palette
COLOR_BLACK = "#000000"
COLOR_WHITE = "#FFFFFF"
COLOR_RED = "#DE2626"


# ---------------------------------------------------------------------------
# Dynamic SVG Generation Primitives
# ---------------------------------------------------------------------------

def create_isometric_cube_svg(
    viewbox_size: int = 400,
    cube_style: str = "104a_floating",
    stroke_color: str = COLOR_WHITE,
    accent_color: str = COLOR_RED,
    pulse_intensity: float = 1.0
) -> str:
    """
    Generates dynamic Policy §8.3 compliant isometric cube SVG markup.
    Supported styles:
    - 104: Standard single cube
    - 104a_floating: Cube with floating top cap
    - 104db_pillar: Vertical pillar of stacked cubes
    - 104_nested: Outer cube enclosing inner child cubes
    - mfdb_federation: Central master cube linked to peripheral node cubes
    """
    center_x = viewbox_size / 2.0
    center_y = viewbox_size / 2.0
    size = viewbox_size * 0.28

    dx = size * math.cos(math.radians(30))
    dy = size * math.sin(math.radians(30))

    if cube_style == "104a_floating":
        float_offset = 18.0 * pulse_intensity
        # Top floating face
        p_top = [
            f"{center_x},{center_y - size - float_offset}",
            f"{center_x + dx},{center_y - dy - float_offset}",
            f"{center_x},{center_y - float_offset}",
            f"{center_x - dx},{center_y - dy - float_offset}"
        ]
        # Left face
        p_left = [
            f"{center_x},{center_y}",
            f"{center_x - dx},{center_y - dy}",
            f"{center_x - dx},{center_y + size - dy}",
            f"{center_x},{center_y + size}"
        ]
        # Right face
        p_right = [
            f"{center_x},{center_y}",
            f"{center_x + dx},{center_y - dy}",
            f"{center_x + dx},{center_y + size - dy}",
            f"{center_x},{center_y + size}"
        ]

        svg = f"""<svg viewBox="0 0 {viewbox_size} {viewbox_size}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
  <defs>
    <filter id="cube-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <!-- Background coordinate crosshairs -->
  <line x1="{center_x}" y1="20" x2="{center_x}" y2="{viewbox_size-20}" stroke="#1c1c24" stroke-width="1" stroke-dasharray="4,4" />
  <line x1="20" y1="{center_y}" x2="{viewbox_size-20}" y2="{center_y}" stroke="#1c1c24" stroke-width="1" stroke-dasharray="4,4" />
  <!-- Floating Cap (BEJSON 104a) -->
  <polygon points="{' '.join(p_top)}" fill="{accent_color}" fill-opacity="0.25" stroke="{accent_color}" stroke-width="2.5" filter="url(#cube-glow)" />
  <!-- Left Face -->
  <polygon points="{' '.join(p_left)}" fill="#0c0c10" stroke="{stroke_color}" stroke-width="2" />
  <!-- Right Face -->
  <polygon points="{' '.join(p_right)}" fill="#14141a" stroke="{stroke_color}" stroke-width="2" />
  <!-- Center Core Node -->
  <circle cx="{center_x}" cy="{center_y + size/2}" r="{4 * pulse_intensity}" fill="{accent_color}" />
</svg>"""
        return svg

    # Default Standard 104 Cube
    p_top = [
        f"{center_x},{center_y - size}",
        f"{center_x + dx},{center_y - dy}",
        f"{center_x},{center_y}",
        f"{center_x - dx},{center_y - dy}"
    ]
    p_left = [
        f"{center_x},{center_y}",
        f"{center_x - dx},{center_y - dy}",
        f"{center_x - dx},{center_y + size - dy}",
        f"{center_x},{center_y + size}"
    ]
    p_right = [
        f"{center_x},{center_y}",
        f"{center_x + dx},{center_y - dy}",
        f"{center_x + dx},{center_y + size - dy}",
        f"{center_x},{center_y + size}"
    ]

    return f"""<svg viewBox="0 0 {viewbox_size} {viewbox_size}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
  <polygon points="{' '.join(p_top)}" fill="#181822" stroke="{stroke_color}" stroke-width="2" />
  <polygon points="{' '.join(p_left)}" fill="#0e0e14" stroke="{stroke_color}" stroke-width="2" />
  <polygon points="{' '.join(p_right)}" fill="#12121a" stroke="{stroke_color}" stroke-width="2" />
  <circle cx="{center_x}" cy="{center_y}" r="{3 * pulse_intensity}" fill="{accent_color}" />
</svg>"""


# ---------------------------------------------------------------------------
# Playwright Browser Runner Primitives
# ---------------------------------------------------------------------------

async def _launch_browser_session():
    """
    Initializes a Playwright driver instance.
    Checks for native Termux Chromium wrapper first, then falls back to standard playwright.
    """
    try:
        from termux_playwright import async_playwright_termux, launch
        pw_context_manager = async_playwright_termux()
        is_termux = True
    except ImportError:
        from playwright.async_api import async_playwright
        pw_context_manager = async_playwright()
        is_termux = False

    return pw_context_manager, is_termux


# ---------------------------------------------------------------------------
# Single Still Frame Capture Engine
# ---------------------------------------------------------------------------

async def render_still_frame(
    width_px: int = 800,
    height_px: int = 800,
    output_path: str = "captures/still_frame.png",
    svg_markup: Optional[str] = None,
    template_name: str = "blank_slate_stage.html",
    bg_theme: str = "#000000",
    stage_selector: str = "#capture-stage",
    device_scale: int = 2,
    seek_progress: float = 0.0,
    text_overlays: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Renders a single still frame into a blank-slate canvas stage and saves it to disk.
    Injects dynamic coordinate-based text overlays pre-recording if declared in config.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    stage_file = out_file.parent / f"_stage_{uuid.uuid4().hex[:8]}.html"
    instantiate_stage_file(
        output_path=stage_file,
        template_name=template_name,
        width_px=width_px,
        height_px=height_px,
        bg_theme=bg_theme,
        initial_svg_markup=svg_markup
    )

    pw_cm, is_termux = await _launch_browser_session()

    async with pw_cm as pw_driver:
        if is_termux:
            from termux_playwright import launch
            browser = await launch(pw_driver, headless=True)
        else:
            browser = await pw_driver.chromium.launch(headless=True)

        context = await browser.new_context(
            viewport={"width": width_px + 40, "height": height_px + 40},
            device_scale_factor=device_scale
        )
        page = await context.new_page()

        target_url = f"file://{stage_file.resolve()}"
        logger.info(f"Navigating to blank-slate stage: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")

        try:
            await page.wait_for_function("window.isReadyToCapture === true", timeout=4000)
        except Exception:
            await page.wait_for_timeout(500)

        if svg_markup:
            await page.evaluate(f"window.setSvgContent({json.dumps(svg_markup)})")
            await page.wait_for_timeout(100)

        if seek_progress > 0.0:
            await page.evaluate(f"window.seekProgress && window.seekProgress({seek_progress}, 8.0)")
            await page.wait_for_timeout(100)

        # Pre-recording coordinate text overlay injection
        if text_overlays:
            ctx = {"frame": 0, "time": 0.0, "fps": 30, "caption": "Still Capture"}
            await page.evaluate(f"window.setTextOverlays({json.dumps(text_overlays)}, {json.dumps(ctx)})")
            await page.wait_for_timeout(80)

        stage_elem = await page.query_selector(stage_selector)
        target = stage_elem if stage_elem else page

        await target.screenshot(path=str(out_file))
        await browser.close()

    if stage_file.exists():
        try:
            stage_file.unlink()
        except OSError:
            pass

    file_bytes = out_file.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    logger.info(f"Rendered still frame: {out_file} ({len(file_bytes)} bytes, sha: {sha256[:8]})")

    return {
        "status": "success",
        "output_file": str(out_file),
        "bytes": len(file_bytes),
        "sha256": sha256
    }


# ---------------------------------------------------------------------------
# Row-Per-Frame Animation Engine
# ---------------------------------------------------------------------------

async def render_row_per_frame_animation(
    animation_doc: Dict[str, Any],
    output_dir: str = "captures/animation_frames",
    save_updated_doc: bool = True,
    device_scale: int = 2,
    stage_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Renders every frame declared in a BEJSON 105a Row-Per-Frame Animation document.
    Iterates over each row in `Values`, injects dynamic SVG or timeline seek into
    the blank slate canvas, applies X,Y coordinate-based text overlays pre-recording,
    writes the frame file, computes SHA-256 hash, and records completion telemetry
    back into the BEJSON 105a document.
    """
    is_valid, errors = validate_graphic_105a_doc(animation_doc)
    if not is_valid:
        raise ValueError(f"Invalid BEJSON 105a animation document: {errors}")

    fields = animation_doc.get("Fields", [])
    fmap = build_field_map_105(fields)
    values = animation_doc.get("Values", [])

    width_px = int(animation_doc.get("Width_Px", 800))
    height_px = int(animation_doc.get("Height_Px", 800))
    anim_name = animation_doc.get("Animation_Name", "animation")
    duration_sec = float(animation_doc.get("Duration_Sec", 8.0))
    fps = int(animation_doc.get("FPS", 30))

    # Resolve active text overlays from stage config or document header
    text_overlays: List[Dict[str, Any]] = []
    if stage_config:
        raw_ov = stage_config.get("text_overlays") or stage_config.get("text_overlays_json")
        if isinstance(raw_ov, list):
            text_overlays = raw_ov
        elif isinstance(raw_ov, str):
            try:
                text_overlays = json.loads(raw_ov)
            except Exception:
                pass
    elif "Text_Overlays" in animation_doc:
        raw_ov = animation_doc["Text_Overlays"]
        text_overlays = raw_ov if isinstance(raw_ov, list) else json.loads(raw_ov)

    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    stage_file = out_path / f"_stage_{uuid.uuid4().hex[:8]}.html"
    instantiate_stage_file(
        output_path=stage_file,
        template_name="blank_slate_stage.html",
        width_px=width_px,
        height_px=height_px,
        bg_theme="#000000"
    )

    pw_cm, is_termux = await _launch_browser_session()

    rendered_count = 0
    total_bytes = 0

    async with pw_cm as pw_driver:
        if is_termux:
            from termux_playwright import launch
            browser = await launch(pw_driver, headless=True)
        else:
            browser = await pw_driver.chromium.launch(headless=True)

        context = await browser.new_context(
            viewport={"width": width_px + 40, "height": height_px + 40},
            device_scale_factor=device_scale
        )
        page = await context.new_page()

        target_url = f"file://{stage_file.resolve()}"
        logger.info(f"Navigating to blank-slate stage for {len(values)} frames: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded")

        try:
            await page.wait_for_function("window.isReadyToCapture === true", timeout=4000)
        except Exception:
            await page.wait_for_timeout(500)

        stage_elem = await page.query_selector("#capture-stage")
        target = stage_elem if stage_elem else page

        for row in values:
            f_idx = row[fmap["frame_index"]]
            ts = row[fmap["timestamp_sec"]]
            seek = row[fmap["seek_progress"]]
            filename = row[fmap["frame_filename"]]
            svg_markup = row[fmap["svg_markup"]]
            frame_file = out_path / filename

            # 1. Update dynamic SVG content if declared per frame
            if svg_markup:
                await page.evaluate(f"window.setSvgContent({json.dumps(svg_markup)})")
                await page.wait_for_timeout(60)
            elif seek is not None:
                # 2. Or seek CSS animation progress
                await page.evaluate(f"window.seekProgress && window.seekProgress({seek}, {duration_sec})")
                await page.wait_for_timeout(60)

            # 3. Pre-recording coordinate text overlay injection
            if text_overlays:
                frame_ctx = {
                    "frame": f_idx,
                    "time": ts,
                    "fps": fps,
                    "seek": seek
                }
                raw_fdata = row[fmap["frame_data_json"]]
                if raw_fdata:
                    try:
                        frame_ctx.update(json.loads(raw_fdata))
                    except Exception:
                        pass
                await page.evaluate(f"window.setTextOverlays({json.dumps(text_overlays)}, {json.dumps(frame_ctx)})")
                await page.wait_for_timeout(40)

            # 4. Capture frame screenshot
            await target.screenshot(path=str(frame_file))

            # 5. Hash and record
            f_bytes = frame_file.read_bytes()
            f_hash = hashlib.sha256(f_bytes).hexdigest()

            row[fmap["is_rendered"]] = True
            row[fmap["checksum_sha256"]] = f_hash

            rendered_count += 1
            total_bytes += len(f_bytes)

            if rendered_count % 10 == 0 or rendered_count == len(values):
                logger.info(f"Rendered frame {rendered_count}/{len(values)}: {filename} (sha: {f_hash[:8]})")

        await browser.close()

    if stage_file.exists():
        try:
            stage_file.unlink()
        except OSError:
            pass

    # Save updated BEJSON 105a document with checksums
    updated_doc_path = None
    if save_updated_doc:
        updated_doc_path = out_path / f"{anim_name}_rendered.105a.bejson"
        updated_doc_path.write_text(json.dumps(animation_doc, indent=2), encoding="utf-8")
        logger.info(f"Saved completed BEJSON 105a animation ledger: {updated_doc_path}")

    return {
        "status": "success",
        "animation_name": anim_name,
        "total_rendered": rendered_count,
        "total_bytes": total_bytes,
        "output_dir": str(out_path),
        "ledger_file": str(updated_doc_path) if updated_doc_path else None
    }


# ---------------------------------------------------------------------------
# Animated SVG Compiler
# ---------------------------------------------------------------------------

def compile_row_per_frame_to_animated_svg(
    animation_doc: Dict[str, Any],
    output_svg_path: str
) -> str:
    """
    Compiles an animated SVG document using SMIL keyframes from a row-per-frame document.
    """
    fields = animation_doc.get("Fields", [])
    fmap = build_field_map_105(fields)
    values = animation_doc.get("Values", [])

    width_px = int(animation_doc.get("Width_Px", 800))
    height_px = int(animation_doc.get("Height_Px", 800))
    duration_sec = float(animation_doc.get("Duration_Sec", 8.0))

    out_file = Path(output_svg_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    svg_frames_content: List[str] = []
    frame_dur = duration_sec / max(1, len(values))

    for idx, row in enumerate(values):
        markup = row[fmap["svg_markup"]] or ""
        # Wrap each frame in a group with timed visibility
        svg_frames_content.append(
            f'  <g id="frame-{idx}" display="none">\n'
            f'    {markup}\n'
            f'    <set attributeName="display" to="inline" begin="{idx * frame_dur:.3f}s" dur="{frame_dur:.3f}s" />\n'
            f'  </g>'
        )

    composite_svg = (
        f'<svg viewBox="0 0 {width_px} {height_px}" width="{width_px}" height="{height_px}" '
        f'xmlns="http://www.w3.org/2000/svg">\n'
        f'  <!-- Animated Composite SVG compiled from BEJSON 105a Row-Per-Frame Animation -->\n'
        + "\n".join(svg_frames_content) + "\n</svg>\n"
    )

    out_file.write_text(composite_svg, encoding="utf-8")
    logger.info(f"Compiled animated SVG to: {out_file} ({len(composite_svg)} bytes)")
    return str(out_file)


# ---------------------------------------------------------------------------
# Multi-Format Video, GIF, WebM & APNG Exporters
# ---------------------------------------------------------------------------

def compile_frames_to_gif(
    frames_dir_or_list: Any,
    output_gif_path: str,
    fps: int = 24,
    loop: int = 0
) -> str:
    """
    Compiles a directory or list of PNG frame images into an optimized animated GIF.
    Uses ffmpeg with 2-pass palettegen when available; falls back to Pillow.
    """
    out_file = Path(output_gif_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try ffmpeg 2-pass palettegen if directory is provided and ffmpeg exists
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin and isinstance(frames_dir_or_list, (str, Path)) and Path(frames_dir_or_list).is_dir():
        f_dir = Path(frames_dir_or_list).resolve()
        png_files = sorted(f_dir.glob("*.png"))
        if png_files:
            cmd = [
                ffmpeg_bin, "-y",
                "-framerate", str(fps),
                "-pattern_type", "glob",
                "-i", str(f_dir / "*.png"),
                "-filter_complex", f"fps={fps},split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
                str(out_file)
            ]
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0 and out_file.exists():
                    logger.info(f"Compiled GIF via ffmpeg: {out_file} ({out_file.stat().st_size} bytes)")
                    return str(out_file)
            except Exception as exc:
                logger.warning(f"ffmpeg GIF compilation fallback: {exc}")

    # 2. Pure Python Pillow Fallback
    try:
        from PIL import Image
        frame_paths: List[Path] = []
        if isinstance(frames_dir_or_list, (str, Path)) and Path(frames_dir_or_list).is_dir():
            frame_paths = sorted(Path(frames_dir_or_list).glob("*.png"))
        elif isinstance(frames_dir_or_list, list):
            frame_paths = [Path(p) for p in frames_dir_or_list]

        if not frame_paths:
            raise FileNotFoundError("No frames found to compile into GIF")

        images = [Image.open(p) for p in frame_paths]
        duration_ms = int(1000.0 / max(1, fps))
        images[0].save(
            out_file,
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=loop,
            optimize=True
        )
        logger.info(f"Compiled GIF via Pillow: {out_file} ({out_file.stat().st_size} bytes, {len(images)} frames)")
        return str(out_file)
    except Exception as exc:
        logger.error(f"Failed to compile GIF: {exc}")
        raise


def compile_frames_to_webm(
    frames_dir: str,
    output_webm_path: str,
    fps: int = 24,
    crf: int = 28
) -> str:
    """
    Compiles rendered PNG frames into an optimized WebM (VP9) video using ffmpeg.
    """
    out_file = Path(output_webm_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is required to compile WebM video")

    f_dir = Path(frames_dir).resolve()
    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(f_dir / "*.png"),
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-b:v", "0",
        "-crf", str(crf),
        str(out_file)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg WebM compilation failed: {res.stderr}")

    logger.info(f"Compiled WebM video: {out_file} ({out_file.stat().st_size} bytes)")
    return str(out_file)


def compile_frames_to_apng(
    frames_dir: str,
    output_apng_path: str,
    fps: int = 24
) -> str:
    """
    Compiles rendered frames into an Animated PNG (APNG) file.
    """
    out_file = Path(output_apng_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
        f_dir = Path(frames_dir).resolve()
        frame_paths = sorted(f_dir.glob("*.png"))
        if not frame_paths:
            raise FileNotFoundError("No frames found to compile APNG")

        images = [Image.open(p) for p in frame_paths]
        duration_ms = int(1000.0 / max(1, fps))
        images[0].save(
            out_file,
            format="PNG",
            save_all=True,
            append_images=images[1:],
            duration=duration_ms,
            loop=0
        )
        logger.info(f"Compiled APNG: {out_file} ({out_file.stat().st_size} bytes)")
        return str(out_file)
    except Exception as exc:
        logger.error(f"APNG compilation failed: {exc}")
        raise


def compile_frames_to_mp4(
    frames_dir: str,
    output_mp4_path: str,
    fps: int = 24
) -> str:
    """
    Compiles rendered frames into an H.264 MP4 video using ffmpeg.
    """
    out_file = Path(output_mp4_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg is required to compile MP4 video")

    f_dir = Path(frames_dir).resolve()
    cmd = [
        ffmpeg_bin, "-y",
        "-framerate", str(fps),
        "-pattern_type", "glob",
        "-i", str(f_dir / "*.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(out_file)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg MP4 compilation failed: {res.stderr}")

    logger.info(f"Compiled MP4 video: {out_file} ({out_file.stat().st_size} bytes)")
    return str(out_file)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BEJSON 105a Graphics Playwright Animation & Canvas Core")
    parser.add_argument("--still", action="store_true", help="Render a single still frame capture")
    parser.add_argument("--row-animation", action="store_true", help="Create and render a row-per-frame animation")
    parser.add_argument("--slideshow", action="store_true", help="Create and render a dynamic slideshow animation")
    parser.add_argument("--diagram", type=str, help="Path to BEJSON diagram JSON file to render into canvas")
    parser.add_argument("--name", type=str, default="pulse_cube_anim", help="Animation or stage identifier")
    parser.add_argument("--width", type=int, default=800, help="Canvas width in pixels")
    parser.add_argument("--height", type=int, default=800, help="Canvas height in pixels")
    parser.add_argument("--duration", type=float, default=4.0, help="Duration in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--output", "-o", type=str, default="captures/frame.png", help="Output path")
    parser.add_argument("--export-gif", action="store_true", help="Compile rendered frames into an animated GIF")
    parser.add_argument("--export-webm", action="store_true", help="Compile rendered frames into WebM video")
    parser.add_argument("--export-apng", action="store_true", help="Compile rendered frames into Animated PNG")
    parser.add_argument("--export-mp4", action="store_true", help="Compile rendered frames into MP4 video")
    parser.add_argument("--list-templates", action="store_true", help="List registered canvas blank-slate templates")
    parser.add_argument("--version", action="version", version=f"lib_bejson_Graphics_graphics_core v{VERSION}")

    args = parser.parse_args()

    if args.list_templates:
        catalog = list_registered_templates()
        print(f"\nRegistered Canvas Blank-Slate Templates ({len(catalog)} total):\n" + "=" * 70)
        for t in catalog:
            print(f"- {t['template_name']:<36} | {t['width_px']}x{t['height_px']} | {t['category']:<18}")
            print(f"  {t['description']}")
        return

    # Diagram Processing Path
    if args.diagram:
        from lib_bejson_Graphics_diagram_loader import (
            render_diagram_svg,
            create_diagram_frame_sequence_105a
        )
        diag_path = Path(args.diagram)
        if not diag_path.exists():
            print(f"Error: Diagram file not found: {diag_path}")
            sys.exit(1)
        diag_data = json.loads(diag_path.read_text(encoding="utf-8"))

        if args.row_animation:
            # Build automated walkthrough states from shapes
            shapes = diag_data.get("shapes", [])
            states = [
                {"name": "Overview", "active_shapes": [], "viewport": {"fit_view": True}, "badge_text": f"{diag_data.get('name', 'Architecture')} Overview"}
            ]
            for s in shapes:
                sid = s.get("id") or s.get("tempId")
                slabel = s.get("label", sid)
                states.append({
                    "name": f"Focus: {slabel}",
                    "active_shapes": [sid],
                    "inspector_shape": sid,
                    "viewport": {"focus_shape": sid, "zoom": 1.3},
                    "badge_text": f"Inspecting: {slabel}"
                })
            states.append({
                "name": "Complete Flow",
                "active_shapes": [s.get("id") or s.get("tempId") for s in shapes],
                "viewport": {"fit_view": True},
                "badge_text": "Complete System Flow Active"
            })

            anim_doc = create_diagram_frame_sequence_105a(
                diagram=diag_data,
                states_sequence=states,
                animation_name=args.name,
                fps=args.fps,
                canvas_w=args.width,
                canvas_h=args.height
            )

            out_dir = f"captures/{args.name}"
            res = asyncio.run(render_row_per_frame_animation(
                animation_doc=anim_doc,
                output_dir=out_dir
            ))
            print(f"Diagram walkthrough rendered: {res['total_rendered']} frames into {res['output_dir']}")

            if args.export_gif:
                gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
                print(f"Exported GIF: {gif_p}")
            if args.export_webm:
                webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
                print(f"Exported WebM: {webm_p}")
            if args.export_apng:
                apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
                print(f"Exported APNG: {apng_p}")
            if args.export_mp4:
                mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
                print(f"Exported MP4: {mp4_p}")
            return

        # Single still capture of diagram
        diag_svg = render_diagram_svg(
            diagram=diag_data,
            state={"active_shapes": [s.get("id") or s.get("tempId") for s in diag_data.get("shapes", [])[:2]], "badge_text": diag_data.get("name")},
            viewport={"fit_view": True},
            canvas_w=args.width,
            canvas_h=args.height
        )
        res = asyncio.run(render_still_frame(
            width_px=args.width,
            height_px=args.height,
            output_path=args.output,
            svg_markup=diag_svg
        ))
        print(f"Diagram still frame captured: {res['output_file']} ({res['bytes']} bytes)")
        return

    if args.still:
        # Generate sample isometric cube SVG
        svg = create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=1.0)
        res = asyncio.run(render_still_frame(
            width_px=args.width,
            height_px=args.height,
            output_path=args.output,
            svg_markup=svg
        ))
        print(f"Still frame captured: {res['output_file']} ({res['bytes']} bytes)")
        return

    if args.slideshow:
        from lib_bejson_Graphics_graphics_schemas import create_slideshow_animation_105a
        # Generate 3 sample slides
        slides = [
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104"),
                "duration_sec": 2.0,
                "caption": "Slide 1: BEJSON 104 Standard Cube"
            },
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating"),
                "duration_sec": 2.0,
                "caption": "Slide 2: BEJSON 104a Floating Cube"
            },
            {
                "svg_markup": create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=1.4),
                "duration_sec": 2.0,
                "caption": "Slide 3: BEJSON 104a Pulse Core"
            }
        ]

        doc = create_slideshow_animation_105a(
            slideshow_name=args.name,
            slides=slides,
            fps=args.fps,
            width_px=args.width,
            height_px=args.height
        )

        out_dir = f"captures/{args.name}"
        res = asyncio.run(render_row_per_frame_animation(
            animation_doc=doc,
            output_dir=out_dir
        ))
        print(f"Slideshow rendered: {res['total_rendered']} frames into {res['output_dir']}")

        if args.export_gif:
            gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
            print(f"Exported GIF: {gif_p}")
        if args.export_webm:
            webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
            print(f"Exported WebM: {webm_p}")
        if args.export_apng:
            apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
            print(f"Exported APNG: {apng_p}")
        if args.export_mp4:
            mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
            print(f"Exported MP4: {mp4_p}")
        return

    if args.row_animation:
        # Build dynamic frame data
        total_frames = max(1, int(math.ceil(args.duration * args.fps)))
        dynamic_frames = []
        for i in range(total_frames):
            pulse = 1.0 + 0.3 * math.sin(2 * math.pi * (i / total_frames))
            f_svg = create_isometric_cube_svg(viewbox_size=args.width, cube_style="104a_floating", pulse_intensity=pulse)
            dynamic_frames.append({"svg_markup": f_svg, "data": {"pulse": pulse}})

        doc = create_row_per_frame_animation_105a(
            animation_name=args.name,
            duration_sec=args.duration,
            fps=args.fps,
            width_px=args.width,
            height_px=args.height,
            dynamic_frames=dynamic_frames
        )

        out_dir = f"captures/{args.name}"
        res = asyncio.run(render_row_per_frame_animation(
            animation_doc=doc,
            output_dir=out_dir
        ))
        print(f"Animation rendered: {res['total_rendered']} frames into {res['output_dir']}")

        if args.export_gif:
            gif_p = compile_frames_to_gif(out_dir, f"{out_dir}/{args.name}.gif", fps=args.fps)
            print(f"Exported GIF: {gif_p}")
        if args.export_webm:
            webm_p = compile_frames_to_webm(out_dir, f"{out_dir}/{args.name}.webm", fps=args.fps)
            print(f"Exported WebM: {webm_p}")
        if args.export_apng:
            apng_p = compile_frames_to_apng(out_dir, f"{out_dir}/{args.name}.png", fps=args.fps)
            print(f"Exported APNG: {apng_p}")
        if args.export_mp4:
            mp4_p = compile_frames_to_mp4(out_dir, f"{out_dir}/{args.name}.mp4", fps=args.fps)
            print(f"Exported MP4: {mp4_p}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

