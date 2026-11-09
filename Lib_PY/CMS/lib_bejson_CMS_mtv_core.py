"""
Name:           lib_bejson_CMS_mtv_core.py
Family:         CMS
Module Purpose: Foundational data contracts, Format 105 entity schemas, and pre-built
                taxonomy archetypes for the Taxonomy-Driven MTV Scaffolding Engine.
Version:        100
Release_Version: 300
Date Created:   2026-11-06
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  9a3c7e14-2b5d-4f80-8c29-3d1f05e94b81
"""

from __future__ import annotations

import os
import sys
import re
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Ensure sibling library families in libraries_105 resolve dynamically
CURRENT_MODULE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
LIBRARIES_105_ROOT_DIRECTORY = os.path.normpath(os.path.join(CURRENT_MODULE_DIRECTORY, "..", ".."))
LIB_PY_DIRECTORY = os.path.join(LIBRARIES_105_ROOT_DIRECTORY, "Lib_PY")

for sibling_family_folder_name in ("Core", "Taxonomies", "Tax_Scaffolds", "Standards", "Canvas", "Graphics"):
    resolved_family_path = os.path.join(LIB_PY_DIRECTORY, sibling_family_folder_name)
    if os.path.isdir(resolved_family_path) and resolved_family_path not in sys.path:
        sys.path.insert(0, resolved_family_path)

# Regex validators for RFC 4122 v4 UUID and snake_case tokens
UUID4_PATTERN_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
SNAKE_CASE_PATTERN_REGEX = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*\Z")

# Canonical 105 primitive types
ALLOWED_BEJSON_PRIMITIVE_TYPES = ("string", "integer", "number", "float", "boolean", "null", "array", "object")

# ---------------------------------------------------------------------------
# O(1) Field Map Cache & Boundary Sanitization
# ---------------------------------------------------------------------------
def bejson_105_get_field_map(bejson_document_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Constructs and returns an O(1) field map cache dictionary mapping canonical
    field names to their integer column indices in the Values table.
    Guarantees zero brittle positional indexing.
    """
    field_definitions_list = bejson_document_data.get("Fields", [])
    compiled_field_map_cache: Dict[str, int] = {}
    for column_index_metric, field_definition_dictionary in enumerate(field_definitions_list):
        field_identifier_name = field_definition_dictionary.get("name", "").strip()
        if field_identifier_name:
            compiled_field_map_cache[field_identifier_name] = column_index_metric
    return compiled_field_map_cache


def bejson_105_sanitize_boundary_value(raw_boundary_cell_value: Any) -> Any:
    """
    Sanitizes string and primitive values at input boundaries per Policy §10.9.
    Strips leading and trailing whitespace from string inputs.
    """
    if isinstance(raw_boundary_cell_value, str):
        return raw_boundary_cell_value.strip()
    return raw_boundary_cell_value


def bejson_105_mint_uuid() -> str:
    """Generates an immutable RFC 4122 Version 4 UUID string."""
    return str(uuid.uuid4())


def bejson_105_construct_field_descriptor(
    field_name_identifier: str,
    field_primitive_type: str,
    field_uuid_identifier: Optional[str] = None,
    foreign_key_target_entity: Optional[str] = None,
    foreign_key_on_delete_behavior: Optional[str] = None,
    field_description_text: str = ""
) -> Dict[str, Any]:
    """
    Constructs a verified Format 105 schema field descriptor containing an
    immutable RFC 4122 v4 field_uuid and optional MFDB v1.40 FK constraints.
    """
    sanitized_field_name = field_name_identifier.strip()
    if not SNAKE_CASE_PATTERN_REGEX.match(sanitized_field_name):
        raise ValueError(f"Field name '{sanitized_field_name}' must adhere to strict snake_case format.")

    normalized_type = field_primitive_type.strip().lower()
    if normalized_type not in ALLOWED_BEJSON_PRIMITIVE_TYPES:
        raise ValueError(f"Field type '{normalized_type}' must be one of {ALLOWED_BEJSON_PRIMITIVE_TYPES}.")

    assigned_field_uuid = field_uuid_identifier.strip() if field_uuid_identifier else bejson_105_mint_uuid()
    if not UUID4_PATTERN_REGEX.match(assigned_field_uuid):
        raise ValueError(f"Assigned field_uuid '{assigned_field_uuid}' is not a valid RFC 4122 Version 4 UUID.")

    field_descriptor_object: Dict[str, Any] = {
        "name": sanitized_field_name,
        "type": normalized_type,
        "field_uuid": assigned_field_uuid
    }

    if field_description_text:
        field_descriptor_object["description"] = field_description_text.strip()

    if foreign_key_target_entity:
        field_descriptor_object["fk_target_entity"] = foreign_key_target_entity.strip()
        target_on_delete = (foreign_key_on_delete_behavior or "restrict").strip().lower()
        if target_on_delete not in ("restrict", "cascade", "null"):
            raise ValueError(f"Invalid fk_on_delete behavior '{target_on_delete}'. Must be restrict, cascade, or null.")
        field_descriptor_object["fk_on_delete"] = target_on_delete

    return field_descriptor_object


# ---------------------------------------------------------------------------
# Pre-Built Taxonomy Archetypes Catalog
# ---------------------------------------------------------------------------
CANONICAL_MTV_ARCHETYPES_CATALOG: Dict[str, Dict[str, Any]] = {
    "video_hub": {
        "archetype_id": "video_hub",
        "archetype_name": "Video Streaming & Media Hub",
        "domain_purpose": "Curated video lectures, tutorials, and streaming media channels.",
        "canonical_entity_prefixes": {
            "Category": "cat_",
            "ExternalMedia": "extmedia_",
            "MediaPlaylist": "playlist_"
        },
        "bound_templates": [
            "scaffold_video_feed.html",
            "scaffold_video_player.html",
            "scaffold_media_grid.html"
        ],
        "primary_renderer_class_name": "VideoPageRenderer",
        "entities": [
            {
                "entity_name": "Category",
                "table_description": "Topical category taxonomy for video groupings.",
                "primary_key_column_name": "cat_uuid",
                "entity_prefix": "cat_",
                "fields": [
                    {"name": "cat_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "cat_name", "type": "string", "description": "Display name of the category."},
                    {"name": "cat_slug", "type": "string", "description": "URL-safe routing slug."},
                    {"name": "cat_order_index", "type": "integer", "description": "Sorting sequence order."}
                ]
            },
            {
                "entity_name": "ExternalMedia",
                "table_description": "Curated streaming video and audio references.",
                "primary_key_column_name": "extmedia_uuid",
                "entity_prefix": "extmedia_",
                "fields": [
                    {"name": "extmedia_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "extmedia_title", "type": "string", "description": "Title of the media piece."},
                    {"name": "extmedia_url", "type": "string", "description": "External or embedded stream URL."},
                    {"name": "extmedia_duration_seconds", "type": "integer", "description": "Duration in seconds."},
                    {"name": "extmedia_cat_uuid_fk", "type": "string", "fk_target_entity": "Category", "fk_on_delete": "restrict", "description": "Category foreign key reference."}
                ]
            },
            {
                "entity_name": "MediaPlaylist",
                "table_description": "Sequenced playback queues and media series.",
                "primary_key_column_name": "playlist_uuid",
                "entity_prefix": "playlist_",
                "fields": [
                    {"name": "playlist_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "playlist_title", "type": "string", "description": "Display title of playlist."},
                    {"name": "playlist_media_items_json", "type": "string", "description": "Serialized list of ordered extmedia UUID references."}
                ]
            }
        ]
    },
    "documentation": {
        "archetype_id": "documentation",
        "archetype_name": "Technical Documentation & E-Book Compendium",
        "domain_purpose": "Multi-chapter programming guides, API specifications, and formal manuals.",
        "canonical_entity_prefixes": {
            "Category": "cat_",
            "DocumentRecord": "doc_",
            "SpecificationMetadata": "spec_"
        },
        "bound_templates": [
            "scaffold_document.html",
            "scaffold_consolidated_ebook.html",
            "scaffold_content_page.html"
        ],
        "primary_renderer_class_name": "DocumentPageRenderer",
        "entities": [
            {
                "entity_name": "Category",
                "table_description": "Documentation section taxonomy partitions.",
                "primary_key_column_name": "cat_uuid",
                "entity_prefix": "cat_",
                "fields": [
                    {"name": "cat_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "cat_name", "type": "string", "description": "Category heading title."},
                    {"name": "cat_slug", "type": "string", "description": "URL-safe section path slug."},
                    {"name": "cat_order_index", "type": "integer", "description": "Display order index."}
                ]
            },
            {
                "entity_name": "DocumentRecord",
                "table_description": "Individual technical guide chapters and reference pages.",
                "primary_key_column_name": "doc_uuid",
                "entity_prefix": "doc_",
                "fields": [
                    {"name": "doc_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "doc_title", "type": "string", "description": "Document title."},
                    {"name": "doc_slug", "type": "string", "description": "Leaf page URL slug."},
                    {"name": "doc_toc_level", "type": "integer", "description": "Table-of-contents hierarchy depth level."},
                    {"name": "doc_cat_uuid_fk", "type": "string", "fk_target_entity": "Category", "fk_on_delete": "restrict", "description": "Parent category section reference."},
                    {"name": "doc_body_path", "type": "string", "description": "Relative path to standalone content file."}
                ]
            },
            {
                "entity_name": "SpecificationMetadata",
                "table_description": "Specification attributes, RFC references, and version metadata.",
                "primary_key_column_name": "spec_uuid",
                "entity_prefix": "spec_",
                "fields": [
                    {"name": "spec_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "spec_version_string", "type": "string", "description": "Semantic specification release version."},
                    {"name": "spec_relational_identifier", "type": "string", "description": "Canonical Relational ID."},
                    {"name": "spec_author_credit", "type": "string", "description": "Author attribution credit string."}
                ]
            }
        ]
    },
    "editorial": {
        "archetype_id": "editorial",
        "archetype_name": "Editorial Multi-Author Publication",
        "domain_purpose": "Multi-category journalism, blogs, opinion series, and periodical releases.",
        "canonical_entity_prefixes": {
            "Category": "cat_",
            "AuthorProfile": "author_",
            "PageRecord": "page_"
        },
        "bound_templates": [
            "scaffold_master_index.html",
            "scaffold_feed.html",
            "scaffold_blog_post.html"
        ],
        "primary_renderer_class_name": "StandardPageRenderer",
        "entities": [
            {
                "entity_name": "Category",
                "table_description": "Publication topics and editorial pillars.",
                "primary_key_column_name": "cat_uuid",
                "entity_prefix": "cat_",
                "fields": [
                    {"name": "cat_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "cat_name", "type": "string", "description": "Topic or column title."},
                    {"name": "cat_slug", "type": "string", "description": "URL directory slug."}
                ]
            },
            {
                "entity_name": "AuthorProfile",
                "table_description": "Journalist, author, and researcher profiles.",
                "primary_key_column_name": "author_uuid",
                "entity_prefix": "author_",
                "fields": [
                    {"name": "author_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "author_display_name", "type": "string", "description": "Author byline display name."},
                    {"name": "author_bio_summary", "type": "string", "description": "Short bio narrative summary."},
                    {"name": "author_avatar_relative_path", "type": "string", "description": "Relative asset path for author image."}
                ]
            },
            {
                "entity_name": "PageRecord",
                "table_description": "Chronological article ledger and publication metadata.",
                "primary_key_column_name": "page_uuid",
                "entity_prefix": "page_",
                "fields": [
                    {"name": "page_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "page_title", "type": "string", "description": "Headline article title."},
                    {"name": "page_slug", "type": "string", "description": "Article URL slug."},
                    {"name": "page_author_uuid_fk", "type": "string", "fk_target_entity": "AuthorProfile", "fk_on_delete": "restrict", "description": "Author profile foreign key reference."},
                    {"name": "page_cat_uuid_fk", "type": "string", "fk_target_entity": "Category", "fk_on_delete": "restrict", "description": "Topic category foreign key reference."},
                    {"name": "page_created_at_timestamp", "type": "string", "description": "ISO-8601 UTC publication timestamp."}
                ]
            }
        ]
    },
    "portfolio": {
        "archetype_id": "portfolio",
        "archetype_name": "Creative Portfolio & Digital Showcase",
        "domain_purpose": "Case studies, design portfolios, visual galleries, and project presentations.",
        "canonical_entity_prefixes": {
            "Category": "cat_",
            "ProjectShowcase": "project_",
            "MediaAsset": "asset_"
        },
        "bound_templates": [
            "scaffold_project_showcase.html",
            "scaffold_image_feed.html",
            "scaffold_image_lightbox.html"
        ],
        "primary_renderer_class_name": "ShowcasePageRenderer",
        "entities": [
            {
                "entity_name": "Category",
                "table_description": "Portfolio creative domains and case study classifications.",
                "primary_key_column_name": "cat_uuid",
                "entity_prefix": "cat_",
                "fields": [
                    {"name": "cat_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "cat_name", "type": "string", "description": "Discipline category name."},
                    {"name": "cat_slug", "type": "string", "description": "Discipline route slug."}
                ]
            },
            {
                "entity_name": "ProjectShowcase",
                "table_description": "Curated case studies, engineering builds, and artwork entries.",
                "primary_key_column_name": "project_uuid",
                "entity_prefix": "project_",
                "fields": [
                    {"name": "project_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "project_title", "type": "string", "description": "Showcase project title."},
                    {"name": "project_tech_stack_summary", "type": "string", "description": "Comma-delimited technologies used."},
                    {"name": "project_overview_abstract", "type": "string", "description": "Abstract overview description."},
                    {"name": "project_specs_summary", "type": "string", "description": "Brief structural specifications."},
                    {"name": "project_cat_uuid_fk", "type": "string", "fk_target_entity": "Category", "fk_on_delete": "restrict", "description": "Discipline category reference."}
                ]
            },
            {
                "entity_name": "MediaAsset",
                "table_description": "High-DPI visual renders, vector graphics, and photography assets.",
                "primary_key_column_name": "asset_uuid",
                "entity_prefix": "asset_",
                "fields": [
                    {"name": "asset_uuid", "type": "string", "description": "Synthetic RFC 4122 v4 primary key."},
                    {"name": "asset_filename_path", "type": "string", "description": "Relative filename path."},
                    {"name": "asset_aspect_ratio_token", "type": "string", "description": "Ratio tag (e.g. 16:9, 1:1, 4:3)."},
                    {"name": "asset_caption_text", "type": "string", "description": "Literal descriptive caption label."},
                    {"name": "asset_project_uuid_fk", "type": "string", "fk_target_entity": "ProjectShowcase", "fk_on_delete": "cascade", "description": "Parent showcase project reference."}
                ]
            }
        ]
    }
}


def bejson_cms_get_archetype(archetype_identifier_key: str) -> Dict[str, Any]:
    """Retrieves an archetype definition by key, raising KeyError if not found."""
    normalized_key = archetype_identifier_key.strip().lower()
    if normalized_key not in CANONICAL_MTV_ARCHETYPES_CATALOG:
        available_keys = list(CANONICAL_MTV_ARCHETYPES_CATALOG.keys())
        raise KeyError(f"Archetype '{normalized_key}' not found. Available archetypes: {available_keys}")
    return CANONICAL_MTV_ARCHETYPES_CATALOG[normalized_key]


def bejson_cms_list_archetypes() -> List[Dict[str, Any]]:
    """Returns a summary list of all registered canonical MTV archetypes."""
    summary_list: List[Dict[str, Any]] = []
    for archetype_key, archetype_definition in CANONICAL_MTV_ARCHETYPES_CATALOG.items():
        summary_list.append({
            "archetype_id": archetype_definition["archetype_id"],
            "archetype_name": archetype_definition["archetype_name"],
            "domain_purpose": archetype_definition["domain_purpose"],
            "bound_templates": archetype_definition["bound_templates"],
            "primary_renderer_class_name": archetype_definition["primary_renderer_class_name"],
            "entity_names": [entity_dict["entity_name"] for entity_dict in archetype_definition["entities"]]
        })
    return summary_list
