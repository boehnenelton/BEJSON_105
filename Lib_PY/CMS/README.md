# `lib_bejson_CMS` (Taxonomy-Driven MTV Scaffolding Engine)

- **File Path**: `Lib_PY/CMS/README.md`
- **Purpose**: The 105 Integrity Era MTV (Model-Template-View) Scaffolding Engine & Admin Dashboard.
- **VERSION**: `1.0.0`
- **Release_Version**: `300`
- **Ecosystem**: BEJSON 105 / MFDB v1.40
- **Author**: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
- **RELATIONAL_ID**: `8c19d45a-39b0-4ec1-9876-02a81f364bc9`

---

## 1. Executive Summary & Paradigm

Traditional runtime CMS platforms tie database models, routing tables, and templates together into heavy, ongoing server runtimes with continuous database locks.

`lib_bejson_CMS` shifts from a runtime CMS to a **Taxonomy-Driven MTV (Model-Template-View) Scaffolding Factory**:
1. **Model ($M$)**: Materializes validated BEJSON 105 schema files (`data/<entity>.105.bejson`), MFDB v1.40 master manifests (`105a.mfdb.bejson`), synthetic RFC 4122 v4 UUID primary keys (`record_uuid`), field-level UUIDs (`field_uuid`), and active referential integrity.
2. **Template ($T$)**: Binds zero-filler BEHTML 8-lane scaffold templates from the 13 canonical templates, automatically wiring template tokens to the schema field map.
3. **View ($V$)**: Scaffolds the static publishing pipeline (`build_site.py`) equipped with polymorphic strategy renderers (`StandardPageRenderer`, `VideoPageRenderer`, `DocumentPageRenderer`, `ShowcasePageRenderer`).

---

## 2. Pre-Built Taxonomy Archetypes

| Archetype ID | Archetype Name | Core Entities | Bound Templates | Primary Renderer |
| :--- | :--- | :--- | :--- | :--- |
| `video_hub` | Video Streaming & Media Hub | `Category`, `ExternalMedia`, `MediaPlaylist` | `scaffold_video_feed.html`, `scaffold_video_player.html`, `scaffold_media_grid.html` | `VideoPageRenderer` |
| `documentation` | Technical Documentation & E-Book Compendium | `Category`, `DocumentRecord`, `SpecificationMetadata` | `scaffold_document.html`, `scaffold_consolidated_ebook.html`, `scaffold_content_page.html` | `DocumentPageRenderer` |
| `editorial` | Editorial Multi-Author Publication | `Category`, `AuthorProfile`, `PageRecord` | `scaffold_master_index.html`, `scaffold_feed.html`, `scaffold_blog_post.html` | `StandardPageRenderer` |
| `portfolio` | Creative Portfolio & Digital Showcase | `Category`, `ProjectShowcase`, `MediaAsset` | `scaffold_project_showcase.html`, `scaffold_image_feed.html`, `scaffold_image_lightbox.html` | `ShowcasePageRenderer` |

---

## 3. Python API Quickstart

```python
from pathlib import Path
from Lib_PY.CMS import MTVScaffoldSynthesizer, validate_mtv_project_scaffold

# 1. Instantiate Video Hub archetype
target_dir = Path("./my_video_portal")
synthesizer = MTVScaffoldSynthesizer(target_dir)
report = synthesizer.instantiate_archetype_scaffold("video_hub", "Lecture Series Portal")

# 2. Validate MTV scaffold integrity
validation = validate_mtv_project_scaffold(target_dir)
assert validation["passed"], validation["problems"]
```

---

## 4. Python Backend Admin Dashboard

Launch the interactive administrative dashboard:

```bash
python3 Lib_PY/CMS/web/Scaffold_Admin_Entry.py --port 5020
```

- Port 5020 (non-colliding with legacy runtime CMS ports).
- Features Blueprint Catalog, Custom Taxonomy Builder, and Project Exporter.
- BECSS Tri-Color design discipline (`#060606`, `#FFFFFF`, `#DE2626`).
