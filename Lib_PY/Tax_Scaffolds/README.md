# lib_bejson_Tax_Scaffolds

- **File:** Lib_PY/Tax_Scaffolds/README.md
- **Purpose:** The kid with the crayons: build databases, hand crayon boxes (field sets) to tables (entities), reserve spare columns, link master and slave. BEJSON 105 / MFDB v1.40.
- **VERSION:** 3.0.0
- **RELATIONAL_ID:** 02d1cc40-7040-46f0-9334-82e43b469254
- **Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Never seen this before? Read **START_HERE.md** in the project root first. It has pictures and crayons. This family needs `Taxonomies` and `Core` next to it.

## What is in the box: three files

| Module | Kid version | Technical |
|---|---|---|
| `_core` | The hand: the only code that edits columns | all-or-nothing wrapper (lock, backup, restore), insert columns before Z-space, cache refresh (the family's only private Core import) |
| `_validator` | The teacher: looks before anything is written | `plan_graft`, subject names, audit gate |
| `_scaffold` | The kid with the crayons: everything that builds or changes a node | graft, upgrade, scaffold entities, rebuild and prebuilt deployment, deployments, Z-space slots, federation links |

All calls are `bejson_tax_scaffolds_<name>(...)`.

## Example 1: new database with two pages that share a box

    node = bejson_tax_scaffolds_deploy_rebuild(
        work_folder, "cms-node", "CMS", taxonomy_namespace="cms",
        field_sets=[media_asset_box],
        entities=[
          {"name": "CmsPicture", "fields": [{"name": "cms_picture_label_key", "type": "string"}], "field_sets": ["media_asset"]},
          {"name": "CmsVideo",   "fields": [{"name": "cms_video_label_key",   "type": "string"}], "field_sets": ["media_asset"]}])

Columns made: `cms_picture_title_name`, `cms_video_title_name`, and so on.

## Example 2: add the box to a page that already has rows

    bejson_tax_scaffolds_graft_field_set(manifest, "CmsDocument", "media_asset")

Old rows stay. New columns are empty (null).

## Example 3: pick the page's subject name yourself

    bejson_tax_scaffolds_scaffold_entity(manifest, "cms", "CmsClip",
        [{"name": "cms_clip_label_key", "type": "string"}],
        [{"set_key": "media_asset", "subject": "reel"}])
    # columns: cms_reel_title_name, cms_reel_file_key, ...

Without `subject`, `CmsVideoLibrary` becomes `video_library`.

## Example 4: the box got a new crayon

    bejson_taxonomies_new_version(manifest, "media_asset", [new_member])
    bejson_tax_scaffolds_upgrade_graft(manifest, "CmsPicture", "media_asset")

## When it says no

`GraftError` is raised **before anything is written**; `.problems` is a list of plain sentences. If something fails during the write, every file is restored.

## Rules to remember

1. Grafting makes **new** columns with **new** ids. It is not a copy.
2. New columns go **before** the trailing `_slot` pocket; the pocket and all data stay as they were.
3. Pages must already be known to a taxonomy (scaffold them, or track them first).
4. The library's own `Lattice…` tables cannot take boxes.
5. This family never edits `Core`; it may call Core's private cache helper, from `_core` only (owner-granted, see `clarification.md` §5.6).

## Tests

    python3 Lib_PY/Tax_Scaffolds/tests/test_scaffold.py   # 28
    python3 Lib_PY/Tax_Scaffolds/tests/test_graft.py      # 25
