"""
Name:          lib_bejson_Index_metadata.py
Description:   Fast EXIF metadata, filename pattern, and perceptual hash (dHash + pHash) extractor for recursive image indexing.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:       PolyForm-Noncommercial-1.0.0
RELATIONAL_ID: 7e4a9c10-3b2d-4f88-9a11-c502e81b4502
"""

import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageOps

from .lib_bejson_Index_core import sanitize_boundary_text

Image.MAX_IMAGE_PIXELS = None
logger = logging.getLogger("lib_bejson_Index.metadata")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
FILENAME_PATTERN_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})_(\d+)_(\d+)\.[^.]+$")

# Precompute 32x8 cosine basis for fast separable 2D DCT (top-left 8x8 block)
_DCT_SIZE = 32
_DCT_LOW = 8
_COS_TABLE: List[List[float]] = [
    [
        math.cos(((2 * coord_idx + 1) * freq_idx * math.pi) / (2.0 * _DCT_SIZE))
        for coord_idx in range(_DCT_SIZE)
    ]
    for freq_idx in range(_DCT_LOW)
]


@dataclass
class ImageMetadataRecord:
    """Normalized metadata and perceptual fingerprint for a single image file."""

    image_id: str
    filename: str
    rel_path: str
    ext: str
    file_size_bytes: int
    width: int
    height: int
    aspect_ratio: float
    dhash_hex: str
    phash_hex: str
    exif_datetime_original: str
    exif_datetime_ifd0: str
    filename_date: str
    date_anomaly_flag: bool
    exif_software: str
    exif_make_model: str
    filename_pattern: str
    filename_size_mismatch: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_dhash_hex(gray_image: Image.Image) -> str:
    """Compute 64-bit difference hash (dHash) from grayscale image."""
    resized = gray_image.resize((9, 8), Image.Resampling.BILINEAR)
    pixels = list(resized.getdata())
    diff_bits = 0
    bit_pos = 0
    for row_idx in range(8):
        row_offset = row_idx * 9
        for col_idx in range(8):
            left_pixel = pixels[row_offset + col_idx]
            right_pixel = pixels[row_offset + col_idx + 1]
            if left_pixel > right_pixel:
                diff_bits |= (1 << bit_pos)
            bit_pos += 1
    return f"{diff_bits:016x}"


def compute_phash_hex(gray_image: Image.Image) -> str:
    """Compute 64-bit perceptual hash (pHash) via separable 32x32 DCT."""
    resized = gray_image.resize((_DCT_SIZE, _DCT_SIZE), Image.Resampling.BILINEAR)
    raw_pixels = list(resized.getdata())

    # Step 1: 1D horizontal DCT on rows -> 32 rows x 8 low-freq cols
    horiz: List[List[float]] = []
    for row_idx in range(_DCT_SIZE):
        row_vals = raw_pixels[row_idx * _DCT_SIZE : (row_idx + 1) * _DCT_SIZE]
        row_low: List[float] = []
        for u_freq in range(_DCT_LOW):
            basis = _COS_TABLE[u_freq]
            val = sum(row_vals[k] * basis[k] for k in range(_DCT_SIZE))
            row_low.append(val)
        horiz.append(row_low)

    # Step 2: 1D vertical DCT on columns -> 8x8 low-freq coefficients
    dct_8x8: List[float] = []
    for v_freq in range(_DCT_LOW):
        basis_v = _COS_TABLE[v_freq]
        for u_freq in range(_DCT_LOW):
            val = sum(horiz[row_idx][u_freq] * basis_v[row_idx] for row_idx in range(_DCT_SIZE))
            dct_8x8.append(val)

    # Exclude DC coefficient (index 0) for median calculation
    ac_coefficients = dct_8x8[1:]
    sorted_ac = sorted(ac_coefficients)
    median_val = (sorted_ac[31] + sorted_ac[32]) / 2.0

    phash_bits = 0
    for idx, coeff in enumerate(dct_8x8):
        if coeff > median_val:
            phash_bits |= (1 << idx)
    return f"{phash_bits:016x}"


def hamming_distance_hex(hex_a: str, hex_b: str) -> int:
    """Calculate popcount hamming distance between two 16-hex-char hash strings."""
    if not hex_a or not hex_b:
        return 64
    val_a = int(hex_a, 16)
    val_b = int(hex_b, 16)
    return (val_a ^ val_b).bit_count()


def extract_image_metadata(file_path: Path, base_dir: Path) -> Optional[ImageMetadataRecord]:
    """Inspect image file, extract normalized EXIF, and generate perceptual fingerprints."""
    try:
        stat_res = file_path.stat()
        disk_size = stat_res.st_size
        ext = file_path.suffix.lower()
        rel_path = sanitize_boundary_text(str(file_path.relative_to(base_dir)))

        # Filename date and size pattern inspection
        match = FILENAME_PATTERN_RE.match(file_path.name)
        filename_date = ""
        fn_pattern = "CUSTOM"
        fn_size_mismatch = False
        if match:
            y, m, d, nominal_sz, _salt = match.groups()
            filename_date = f"{y}:{m}:{d}"
            fn_pattern = "YYYY_MM_DD_SIZE_SALT"
            if abs(disk_size - int(nominal_sz)) > 4096:
                fn_size_mismatch = True
        elif file_path.stem.isdigit() and len(file_path.stem) >= 8:
            fn_pattern = "NUMERIC_ID"

        with Image.open(file_path) as img:
            exif_data = img.getexif()
            orig_width, orig_height = img.size

            dt_ifd0 = sanitize_boundary_text(exif_data.get(306, "")) if exif_data else ""
            software = sanitize_boundary_text(exif_data.get(305, "")) if exif_data else ""
            make = sanitize_boundary_text(exif_data.get(271, "")) if exif_data else ""
            model = sanitize_boundary_text(exif_data.get(272, "")) if exif_data else ""
            make_model = f"{make} | {model}".strip(" |") if (make or model) else ""

            exif_ifd = exif_data.get_ifd(0x8769) if exif_data else {}
            dt_orig = sanitize_boundary_text(exif_ifd.get(36867, "")) if exif_ifd else ""

            orientation = exif_data.get(274, 1) if exif_data else 1
            if orientation in (5, 6, 7, 8):
                disp_width, disp_height = orig_height, orig_width
            else:
                disp_width, disp_height = orig_width, orig_height

            if img.format == "JPEG":
                img.draft("L", (64, 64))
            oriented = ImageOps.exif_transpose(img)
            gray_img = oriented.convert("L")
            dhash_hex = compute_dhash_hex(gray_img)
            phash_hex = compute_phash_hex(gray_img)

        date_anomaly = False
        if dt_ifd0 and dt_orig and dt_ifd0[:10] != dt_orig[:10]:
            date_anomaly = True
        elif filename_date and dt_ifd0 and filename_date != dt_ifd0[:10]:
            date_anomaly = True
        elif fn_pattern == "NUMERIC_ID" and not dt_orig and not dt_ifd0:
            date_anomaly = True

        aspect_ratio = round(disp_width / disp_height, 4) if disp_height > 0 else 0.0
        image_id = hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:12]

        return ImageMetadataRecord(
            image_id=image_id,
            filename=file_path.name,
            rel_path=rel_path,
            ext=ext,
            file_size_bytes=disk_size,
            width=disp_width,
            height=disp_height,
            aspect_ratio=aspect_ratio,
            dhash_hex=dhash_hex,
            phash_hex=phash_hex,
            exif_datetime_original=dt_orig,
            exif_datetime_ifd0=dt_ifd0,
            filename_date=filename_date,
            date_anomaly_flag=date_anomaly,
            exif_software=software,
            exif_make_model=make_model,
            filename_pattern=fn_pattern,
            filename_size_mismatch=fn_size_mismatch,
        )
    except Exception as exc:
        logger.warning("Failed to inspect image %s: %s", file_path.name, exc)
        return None
