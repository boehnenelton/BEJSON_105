"""
Name:          lib_bejson_Index_heuristics.py
Description:   Visual perceptual hash clustering engine (Index 1 heuristic) and BEJSON 104a document generator.
Version:       1.0.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
License:       PolyForm-Noncommercial-1.0.0
RELATIONAL_ID: 7e4a9c10-3b2d-4f88-9a11-c502e81b4503
"""

import collections
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .lib_bejson_Index_core import (
    GROUP_SUMMARY_FIELDS,
    IMAGE_INDEX_FIELDS,
    bejson_index_create_doc,
    bejson_index_write_atomic,
)
from .lib_bejson_Index_metadata import ImageMetadataRecord, hamming_distance_hex

logger = logging.getLogger("lib_bejson_Index.heuristics")

RECOMPRESS_SOFTWARE_HINTS = ("shotwell", "picasa", "gimp", "photoshop", "snapseed")


class _DisjointSet:
    """Union-Find structure with deterministic path compression."""

    def __init__(self, count: int) -> None:
        self.parent = list(range(count))

    def find(self, node_idx: int) -> int:
        while self.parent[node_idx] != node_idx:
            self.parent[node_idx] = self.parent[self.parent[node_idx]]
            node_idx = self.parent[node_idx]
        return node_idx

    def union(self, idx_a: int, idx_b: int) -> None:
        root_a = self.find(idx_a)
        root_b = self.find(idx_b)
        if root_a != root_b:
            if root_a < root_b:
                self.parent[root_b] = root_a
            else:
                self.parent[root_a] = root_b


def _candidate_pairs_by_hash_bands(records: List[ImageMetadataRecord]) -> Set[Tuple[int, int]]:
    """Use 4x16-bit band bucketing on dHash and pHash to find near-duplicate candidates in O(N)."""
    buckets: Dict[Tuple[str, int, int], List[int]] = collections.defaultdict(list)
    for idx, rec in enumerate(records):
        d_val = int(rec.dhash_hex, 16)
        p_val = int(rec.phash_hex, 16)
        for band_idx in range(4):
            shift = band_idx * 16
            buckets[("d", band_idx, (d_val >> shift) & 0xFFFF)].append(idx)
            buckets[("p", band_idx, (p_val >> shift) & 0xFFFF)].append(idx)

    pairs: Set[Tuple[int, int]] = set()
    for members in buckets.values():
        if len(members) < 2 or len(members) > 120:
            if len(members) > 120:
                continue
        for pos_i in range(len(members)):
            idx_a = members[pos_i]
            for pos_j in range(pos_i + 1, len(members)):
                idx_b = members[pos_j]
                pairs.add((min(idx_a, idx_b), max(idx_a, idx_b)))
    return pairs


def _is_derivative_software(software: str) -> bool:
    lowered = software.lower()
    return any(hint in lowered for hint in RECOMPRESS_SOFTWARE_HINTS)


def _choose_primary_index(records: List[ImageMetadataRecord], member_indices: List[int]) -> int:
    """Select the canonical primary image in a group (prefer non-derivative, highest pixel area, largest byte size)."""
    def _rank_key(idx: int) -> Tuple[int, int, int, int]:
        rec = records[idx]
        non_deriv = 0 if _is_derivative_software(rec.exif_software) else 1
        non_png = 1 if rec.ext != ".png" else 0
        pixel_area = rec.width * rec.height
        return (non_deriv, non_png, pixel_area, rec.file_size_bytes)

    return max(member_indices, key=_rank_key)


def _classify_layer_role(
    rec: ImageMetadataRecord,
    primary_rec: ImageMetadataRecord,
    is_primary: bool,
    group_size: int,
    hamming_dist: int,
) -> str:
    """Assign a human-readable provenance role to a group member."""
    if group_size == 1:
        return "orphan_singleton"
    if is_primary:
        return "primary_original"
    if rec.ext == ".png" and primary_rec.ext != ".png":
        return "png_conversion"
    if rec.width == primary_rec.width and rec.height == primary_rec.height:
        if rec.file_size_bytes < primary_rec.file_size_bytes:
            return "recompressed_same_res"
        return "duplicate_same_res"
    if (rec.width * rec.height) < (primary_rec.width * primary_rec.height):
        if hamming_dist <= 10:
            return "resized_derivative"
    return "burst_or_angle_sibling"


def cluster_h1_perceptual(
    records: List[ImageMetadataRecord],
) -> Tuple[List[List[int]], Dict[int, Tuple[float, str]]]:
    """H1 / Index 1: Pure Visual Perceptual Hash Clustering (dHash <= 7, pHash <= 9, aspect-ratio guard <= 0.18)."""
    dsu = _DisjointSet(len(records))
    candidate_pairs = _candidate_pairs_by_hash_bands(records)
    pair_reasons: Dict[int, Tuple[float, str]] = {}

    for idx_a, idx_b in candidate_pairs:
        rec_a = records[idx_a]
        rec_b = records[idx_b]
        if abs(rec_a.aspect_ratio - rec_b.aspect_ratio) > 0.18:
            continue
        d_dist = hamming_distance_hex(rec_a.dhash_hex, rec_b.dhash_hex)
        p_dist = hamming_distance_hex(rec_a.phash_hex, rec_b.phash_hex)
        if d_dist <= 7 and p_dist <= 9:
            dsu.union(idx_a, idx_b)
            conf = round(max(0.5, 1.0 - (d_dist + p_dist) / 32.0), 3)
            reason = f"visual_hash(d={d_dist},p={p_dist})"
            pair_reasons[idx_a] = (conf, reason)
            pair_reasons[idx_b] = (conf, reason)

    clusters: Dict[int, List[int]] = collections.defaultdict(list)
    for idx in range(len(records)):
        clusters[dsu.find(idx)].append(idx)
    return list(clusters.values()), pair_reasons


def build_h1_bejson_documents(
    records: List[ImageMetadataRecord],
    output_dir: Path,
) -> Tuple[Path, Path]:
    """Cluster records via Index 1 heuristic and write canonical BEJSON 104a files."""
    raw_clusters, pair_reasons = cluster_h1_perceptual(records)

    # Sort clusters: multi-member groups first (largest first), then singletons
    raw_clusters.sort(key=lambda grp: (-len(grp), records[grp[0]].filename))

    image_rows: List[List[Any]] = []
    group_rows: List[List[Any]] = []

    for grp_num, member_indices in enumerate(raw_clusters, start=1):
        group_id = f"GRP-{grp_num:04d}"
        primary_idx = _choose_primary_index(records, member_indices)
        primary_rec = records[primary_idx]
        group_size = len(member_indices)
        group_label = f"{primary_rec.filename} ({group_size}x)" if group_size > 1 else primary_rec.filename

        widths = [records[idx].width for idx in member_indices]
        total_bytes = sum(records[idx].file_size_bytes for idx in member_indices)
        has_anomaly = any(records[idx].date_anomaly_flag for idx in member_indices)
        hamming_vals: List[int] = []

        ordered_members = sorted(
            member_indices,
            key=lambda idx: (0 if idx == primary_idx else 1, -records[idx].file_size_bytes, records[idx].filename),
        )

        for idx in ordered_members:
            rec = records[idx]
            is_primary = idx == primary_idx
            ham_dist = 0 if is_primary else hamming_distance_hex(rec.dhash_hex, primary_rec.dhash_hex)
            if not is_primary:
                hamming_vals.append(ham_dist)

            layer_role = _classify_layer_role(rec, primary_rec, is_primary, group_size, ham_dist)
            conf_score, match_reason = pair_reasons.get(
                idx,
                (1.0 if group_size == 1 else 0.9, "singleton" if group_size == 1 else "group_anchor"),
            )

            image_rows.append([
                rec.image_id,
                rec.filename,
                rec.rel_path,
                rec.ext,
                rec.file_size_bytes,
                rec.width,
                rec.height,
                rec.aspect_ratio,
                group_id,
                group_label,
                group_size,
                is_primary,
                layer_role,
                rec.dhash_hex,
                rec.phash_hex,
                ham_dist,
                rec.exif_datetime_original,
                rec.exif_datetime_ifd0,
                rec.filename_date,
                rec.date_anomaly_flag,
                rec.exif_software,
                rec.exif_make_model,
                conf_score,
                match_reason,
            ])

        avg_ham = round(sum(hamming_vals) / len(hamming_vals), 2) if hamming_vals else 0.0
        group_type = "singleton" if group_size == 1 else "perceptual_cluster"

        group_rows.append([
            group_id,
            group_label,
            group_type,
            group_size,
            primary_rec.filename,
            min(widths) if widths else 0,
            max(widths) if widths else 0,
            total_bytes,
            has_anomaly,
            avg_ham,
            f"Index 1 visual hash clustering; primary area={primary_rec.width*primary_rec.height}px",
        ])

    output_dir.mkdir(parents=True, exist_ok=True)
    idx_doc = bejson_index_create_doc(
        records_type=["ImageRecord"],
        fields=IMAGE_INDEX_FIELDS,
        values=image_rows,
        schema_name="BEJSON_IMAGE_INDEX_104A",
        schema_version="100",
    )
    sum_doc = bejson_index_create_doc(
        records_type=["GroupSummaryRecord"],
        fields=GROUP_SUMMARY_FIELDS,
        values=group_rows,
        schema_name="BEJSON_GROUP_SUMMARY_104A",
        schema_version="100",
    )

    idx_path = output_dir / "image_index.104a.bejson"
    sum_path = output_dir / "group_summary.104a.bejson"

    bejson_index_write_atomic(idx_path, idx_doc)
    bejson_index_write_atomic(sum_path, sum_doc)

    return idx_path, sum_path
