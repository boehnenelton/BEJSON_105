"""
Name:          lib_bejson_Index/__init__.py
Description:   Package entrypoint for the Index library family in libraries_104.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:       PolyForm-Noncommercial-1.0.0
RELATIONAL_ID: 7e4a9c10-3b2d-4f88-9a11-c502e81b4500
"""

from .lib_bejson_Index_core import (
    GROUP_SUMMARY_FIELDS,
    IMAGE_INDEX_FIELDS,
    SCHEMA_STANDARD_ID,
    bejson_index_create_doc,
    bejson_index_get_field_map,
    bejson_index_load,
    bejson_index_read_col,
    bejson_index_validate_file,
    bejson_index_write_atomic,
    sanitize_boundary_text,
)
from .lib_bejson_Index_metadata import (
    SUPPORTED_EXTENSIONS,
    ImageMetadataRecord,
    compute_dhash_hex,
    compute_phash_hex,
    extract_image_metadata,
    hamming_distance_hex,
)
from .lib_bejson_Index_heuristics import (
    build_h1_bejson_documents,
    cluster_h1_perceptual,
)
from .lib_bejson_Index_scanner import (
    build_recursive_image_index,
    scan_directory_recursive,
)

__all__ = [
    "GROUP_SUMMARY_FIELDS",
    "IMAGE_INDEX_FIELDS",
    "SCHEMA_STANDARD_ID",
    "SUPPORTED_EXTENSIONS",
    "ImageMetadataRecord",
    "bejson_index_create_doc",
    "bejson_index_get_field_map",
    "bejson_index_load",
    "bejson_index_read_col",
    "bejson_index_validate_file",
    "bejson_index_write_atomic",
    "build_h1_bejson_documents",
    "build_recursive_image_index",
    "cluster_h1_perceptual",
    "compute_dhash_hex",
    "compute_phash_hex",
    "extract_image_metadata",
    "hamming_distance_hex",
    "sanitize_boundary_text",
    "scan_directory_recursive",
]
