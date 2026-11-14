"""
Library:         lib_bejson_EBook_core.py
Family:          EBook
Module Purpose:  Core primitives, semantic Markdown parser, manifest engine, and data models for EBook library family.
Architecture:    BEJSON 104 Ecosystem Component maintaining strict schema integrity, O(1) field map caching, and standardized runtime contracts.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0002-e000-11ef-9000-000000000002
License:         PolyForm-Noncommercial-1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import html as html_escape_module
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple
import uuid

try:
    from .lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DOCUMENT_NOT_FOUND,
        E_EBOOK_EMPTY_CONTENT,
        E_EBOOK_MANIFEST_INVALID,
        E_EBOOK_WRITE_FAILED,
        EBookError,
    )
except ImportError:
    from lib_bejson_EBook_bejson_errors import (
        E_EBOOK_DOCUMENT_NOT_FOUND,
        E_EBOOK_EMPTY_CONTENT,
        E_EBOOK_MANIFEST_INVALID,
        E_EBOOK_WRITE_FAILED,
        EBookError,
    )

LOG: logging.Logger = logging.getLogger("bejson_ebook.core")

# ---------------------------------------------------------------------------
# Canonical BEJSON 104a Manifest Schema
# ---------------------------------------------------------------------------
MANIFEST_FIELDS_104A: List[Dict[str, str]] = [
    {"name": "slug", "type": "string"},
    {"name": "title", "type": "string"},
    {"name": "taxonomy", "type": "string"},
    {"name": "source_file", "type": "string"},
    {"name": "source_sha256", "type": "string"},
    {"name": "word_count", "type": "integer"},
    {"name": "reading_time_minutes", "type": "integer"},
    {"name": "sections_count", "type": "integer"},
    {"name": "excerpt", "type": "string"},
    {"name": "subpage_rel_path", "type": "string"},
    {"name": "updated_utc", "type": "string"},
]

MANIFEST_FIELDS_105A: List[Dict[str, str]] = [
    {"name": "record_uuid", "type": "string"},
] + MANIFEST_FIELDS_104A

MANIFEST_FIELDS = MANIFEST_FIELDS_104A


@dataclass
class EBookEntityRecord:
    slug: str
    title: str
    taxonomy: str = "pages"
    source_file: str = ""
    source_sha256: str = ""
    word_count: int = 0
    reading_time_minutes: int = 1
    sections_count: int = 0
    excerpt: str = ""
    subpage_rel_path: str = ""
    updated_utc: str = ""
    record_uuid: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


def compute_file_sha256(file_path: Path, block_size: int = 1048576) -> str:
    """Compute SHA-256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()


def sanitize_slug(text_string: str) -> str:
    """Generate a URL-safe, lowercase slug from arbitrary text."""
    cleaned = re.sub(r"[^\w\s-]", "", text_string).strip().lower()
    return re.sub(r"[-\s]+", "-", cleaned) or "entity"


def format_inline_markdown(text_chunk: str) -> str:
    """Safely format inline Markdown elements into standard semantic HTML5."""
    escaped = html_escape_module.escape(text_chunk)
    # Inline code
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    # Bold italic
    escaped = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", escaped)
    # Bold
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    # Italic
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    # Links: [text](url)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" class="becss-inline-link">\1</a>',
        escaped
    )
    return escaped


def parse_markdown_document(markdown_text: str) -> Dict[str, Any]:
    """
    Parse a Markdown document into structured sections, semantic blocks,
    Table of Contents, word count, and excerpt without tying to audio or transcription.
    """
    if not markdown_text or not markdown_text.strip():
        raise EBookError("Markdown document content is empty", E_EBOOK_EMPTY_CONTENT)

    lines = markdown_text.splitlines()
    title = ""
    sections: List[Dict[str, Any]] = []
    current_section: Dict[str, Any] = {
        "title": "Overview",
        "level": 2,
        "anchor": "section-overview",
        "blocks": [],
        "start_time": ""
    }

    turn_regex = re.compile(r"^\*\*\[([0-9]{2}:[0-9]{2}(?:\s*-\s*[0-9]{2}:[0-9]{2})?)\]\s*(Speaker\s+[A-Za-z0-9]+):\*\*\s*(.*)$")
    speaker_only_regex = re.compile(r"^\*\*(Speaker\s+[A-Za-z0-9]+):\*\*\s*(.*)$")
    section_h2_regex = re.compile(r"^##\s+(.*)$")
    section_h3_regex = re.compile(r"^###\s+(.*)$")

    in_code_block = False
    code_block_lang = ""
    code_block_lines: List[str] = []

    total_words = 0
    all_speakers: List[str] = []
    raw_text_for_excerpt: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Code block fences
        if stripped.startswith("```"):
            if in_code_block:
                # Close code block
                in_code_block = False
                code_content = "\n".join(code_block_lines)
                current_section["blocks"].append({
                    "type": "code",
                    "lang": code_block_lang,
                    "content": code_content
                })
                code_block_lines = []
                code_block_lang = ""
            else:
                in_code_block = True
                code_block_lang = stripped[3:].strip()
                code_block_lines = []
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        if not stripped:
            continue

        # Count words
        words = len(re.findall(r"\b\w+\b", stripped))
        total_words += words

        # Extract H1 Title
        if stripped.startswith("# ") and not title:
            candidate = stripped[2:].strip()
            if candidate.lower().endswith(" transcript"):
                title = candidate[:-11].strip()
            else:
                title = candidate
            continue

        # Extract H2 Section
        h2_match = section_h2_regex.match(stripped)
        if h2_match:
            if current_section["blocks"]:
                sections.append(current_section)
            sec_title = h2_match.group(1).strip()
            # Extract timestamp if present in segment title (e.g. "Segment 1 of 2 — starts 00:00")
            ts_match = re.search(r"starts\s*([0-9]{2}:[0-9]{2})", sec_title, re.IGNORECASE)
            start_ts = ts_match.group(1) if ts_match else ""
            current_section = {
                "title": sec_title,
                "level": 2,
                "anchor": f"sec-{len(sections) + 1}",
                "start_time": start_ts,
                "blocks": []
            }
            continue

        # Extract H3 Sub-section
        h3_match = section_h3_regex.match(stripped)
        if h3_match:
            sub_title = h3_match.group(1).strip()
            current_section["blocks"].append({
                "type": "heading3",
                "title": sub_title,
                "anchor": sanitize_slug(sub_title)
            })
            continue

        # Speaker Dialogue Turn with Timestamp
        turn_match = turn_regex.match(stripped)
        if turn_match:
            ts, spk, turn_text = turn_match.groups()
            if spk not in all_speakers:
                all_speakers.append(spk)
            raw_text_for_excerpt.append(turn_text)
            current_section["blocks"].append({
                "type": "dialogue_turn",
                "timestamp": ts,
                "speaker": spk,
                "text": turn_text
            })
            continue

        # Speaker Dialogue Turn without Timestamp
        spk_match = speaker_only_regex.match(stripped)
        if spk_match:
            spk, turn_text = spk_match.groups()
            if spk not in all_speakers:
                all_speakers.append(spk)
            raw_text_for_excerpt.append(turn_text)
            current_section["blocks"].append({
                "type": "dialogue_turn",
                "timestamp": "",
                "speaker": spk,
                "text": turn_text
            })
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_text = stripped.lstrip("> ").strip()
            raw_text_for_excerpt.append(quote_text)
            current_section["blocks"].append({
                "type": "blockquote",
                "text": quote_text
            })
            continue

        # Bullet list item
        if stripped.startswith(("- ", "* ", "+ ")):
            list_text = stripped[2:].strip()
            current_section["blocks"].append({
                "type": "list_item",
                "text": list_text
            })
            continue

        # Standard Paragraph
        if stripped != "---":
            raw_text_for_excerpt.append(stripped)
            current_section["blocks"].append({
                "type": "paragraph",
                "text": stripped
            })

    if in_code_block and code_block_lines:
        current_section["blocks"].append({
            "type": "code",
            "lang": code_block_lang,
            "content": "\n".join(code_block_lines)
        })

    if current_section["blocks"]:
        sections.append(current_section)

    if not title:
        title = "Untitled Document"

    # Compute excerpt
    excerpt = ""
    for chunk in raw_text_for_excerpt:
        cleaned = re.sub(r"[*_`#\[\]]", "", chunk).strip()
        if len(cleaned) > 20:
            if len(cleaned) > 180:
                excerpt = cleaned[:180].rsplit(" ", 1)[0] + "..."
            else:
                excerpt = cleaned
            break
    if not excerpt:
        excerpt = "Standard structured publication document."

    reading_time = max(1, round(total_words / 180))

    return {
        "title": title,
        "word_count": total_words,
        "reading_time_minutes": reading_time,
        "sections": sections,
        "speakers": all_speakers,
        "excerpt": excerpt,
    }


def bejson_atomic_write(target_path: Path, content_string: str) -> None:
    """Safely write content to disk using write-temp-and-replace semantics."""
    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = target_path.parent
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=temp_dir, delete=False) as tf:
            tf.write(content_string)
            temp_name = tf.name
        os.replace(temp_name, target_path)
    except Exception as e:
        if "temp_name" in locals() and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise EBookError(f"Failed atomic write to {target_path}: {e}", E_EBOOK_WRITE_FAILED)


def load_manifest(manifest_path: Path) -> List[EBookEntityRecord]:
    """Load and deserialize a BEJSON 104a e-book manifest with O(1) field map caching."""
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        return []

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as e:
        raise EBookError(f"Cannot parse manifest JSON: {e}", E_EBOOK_MANIFEST_INVALID)

    fields_header = doc.get("Fields", [])
    values = doc.get("Values", [])
    field_map = {f["name"]: idx for idx, f in enumerate(fields_header)}

    required_keys = ["slug", "title", "subpage_rel_path"]
    for k in required_keys:
        if k not in field_map:
            raise EBookError(f"Manifest missing required field: {k}", E_EBOOK_MANIFEST_INVALID)

    records: List[EBookEntityRecord] = []
    for row in values:
        rec = EBookEntityRecord(
            slug=row[field_map["slug"]],
            title=row[field_map["title"]],
            taxonomy=row[field_map["taxonomy"]] if "taxonomy" in field_map else "pages",
            source_file=row[field_map["source_file"]] if "source_file" in field_map else "",
            source_sha256=row[field_map["source_sha256"]] if "source_sha256" in field_map else "",
            word_count=row[field_map["word_count"]] if "word_count" in field_map else 0,
            reading_time_minutes=row[field_map["reading_time_minutes"]] if "reading_time_minutes" in field_map else 1,
            sections_count=row[field_map["sections_count"]] if "sections_count" in field_map else 0,
            excerpt=row[field_map["excerpt"]] if "excerpt" in field_map else "",
            subpage_rel_path=row[field_map["subpage_rel_path"]],
            updated_utc=row[field_map["updated_utc"]] if "updated_utc" in field_map else "",
            record_uuid=row[field_map["record_uuid"]] if "record_uuid" in field_map else "",
        )
        records.append(rec)
    return records


def save_manifest(manifest_path: Path, records: List[EBookEntityRecord], format_version: str = "104a") -> None:
    """Serialize and save an e-book manifest as a canonical BEJSON 104a or 105a document."""
    manifest_path = Path(manifest_path).resolve()
    is_105 = str(format_version).startswith("105")

    if is_105:
        fields = MANIFEST_FIELDS_105A
        version_tag = "105a"
        values = [
            [
                r.record_uuid or str(uuid.uuid4()),
                r.slug,
                r.title,
                r.taxonomy,
                r.source_file,
                r.source_sha256,
                r.word_count,
                r.reading_time_minutes,
                r.sections_count,
                r.excerpt,
                r.subpage_rel_path,
                r.updated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ]
            for r in records
        ]
    else:
        fields = MANIFEST_FIELDS_104A
        version_tag = "104a"
        values = [
            [
                r.slug,
                r.title,
                r.taxonomy,
                r.source_file,
                r.source_sha256,
                r.word_count,
                r.reading_time_minutes,
                r.sections_count,
                r.excerpt,
                r.subpage_rel_path,
                r.updated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ]
            for r in records
        ]

    doc = {
        "Format": "BEJSON",
        "Format_Version": version_tag,
        "Format_Creator": "Elton Boehnen",
        "Records_Type": ["EBook_Manifest_Record"],
        "Fields": fields,
        "Values": values,
    }

    bejson_atomic_write(manifest_path, json.dumps(doc, indent=2, ensure_ascii=False))
