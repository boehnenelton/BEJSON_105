---
Name: BKS-1_Official_Job_and_Writing_Schemas_and_Rules-V102.md
Description: The official reference card for the BEJSON job schema (JobMaker plan), the writing schema (Book Document and BookType) and the rules that bind them, including the publish rules added after the CMS audit.
Version: 1.0.2 (schema bks-1.0.0)
Date Created: 2026-11-12
Supersedes: the schema, rule and error tables in BKS-1_Final_Schema_and_Architecture-V101.md (the long guide remains the explanatory text)
Format family: BEJSON 104 only (104a plan, 104db Book Document, 104 BookType)
Author: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: 757e3f27-3954-45c8-b9c4-5f58ae6dff84
---

# Official Job Schema, Writing Schema and Rules (BKS-1)

Tables below are generated from the reference registry (`lib/Writing`, BKS_Standard-V115-PKG115), so they match the code. "Req" means required (non-null). Absence is always `null` in Book Documents and BookType files.

---

# Part A. Job schema (the plan)

A job is a **JobMaker job**: BEJSON 104a, `Records_Type ["JobTask"]`. A book plan is a one-way projection of its Book Document. Nothing is added to or removed from JobMaker's schema.

## A.1 File and headers

| Item | Value |
|---|---|
| Location | `jobs/<slug>.bejson` |
| `Format` / `Format_Version` / `Format_Creator` | `BEJSON` / `104a` / `Elton Boehnen` |
| `Schema_Name` / `Schema_Version` | `Job Schema` / `1.0` |
| `Schema_Description` | JobMaker's own text: "Custom job schema for the NewAgent task creation and tracking system, managing individual task states and optional auditing. Each task carries its own task_context (embedded, chunked files), task_reference (path-only refs), and task_mandatory (marks a task as a required, built-in step for the job's Job_Type/Job_Subtype). Job_Type/Job_Subtype classify the job; Contextualize_Plan/Contextualize_Last control what each task is injected with at run time. Also reused unmodified as the Template payload shape." |
| `Job_Goal` | string, non-empty; for books: `Write the book "<title>" for <audience>, in <Language> (<code>). Goal: <goal>` (audience and goal omitted when null) |
| `Job_Type` / `Job_Subtype` | `writing` / `book` for book plans |
| `Contextualize_Plan` / `Contextualize_Last` | boolean; `true` / `true` for books |
| `Job_Complete` | boolean; true only when every task is complete |
| `Creation_Date` / `Completion_Date` | `YYYY-MM-DD` (date only); `Completion_Date` is `""` until complete |
| `Records_Type` | `["JobTask"]` |

No other header is allowed (JobMaker erases extras on save): no `Target_File`, `Execution_Traces` or `Book_*`.

## A.2 Task fields (exactly 11, in this order)

| # | Field | Type |
|--:|---|---|
| 1 | `task_id` | string |
| 2 | `task_order` | integer |
| 3 | `task_name` | string |
| 4 | `task_description` | string |
| 5 | `task_completed` | boolean |
| 6 | `audit_enabled` | boolean |
| 7 | `audit_passed` | boolean |
| 8 | `audit_fail_reason` | string |
| 9 | `task_context` | array |
| 10 | `task_reference` | array |
| 11 | `task_mandatory` | boolean |

## A.3 Task values

| Field | Rule |
|---|---|
| `task_id` | the chapter's UUID (kept by JobMaker on save); unique |
| `task_order` | 1..N over writable nodes, no gaps |
| `task_name` | chapter title, no numbering |
| `task_description` | brief, then a blank line, then derived lines: `Part: <part>` or `Section of: <parent>`, then `Target length: about <N> words.` The first paragraph (the brief) is never empty |
| `task_completed` | true when the chapter is `accepted` |
| `audit_enabled` / `audit_passed` / `audit_fail_reason` | mirror the chapter; before a gate runs `false` / `""` |
| `task_context` | array of `{"ref": "<relative path>", "text_based": true, "chunks": [{"chunk_id","chunk_label","chunk_content","chunk_index_pos","chunk_status"}]}`; real arrays, never a JSON string |
| `task_reference` | array of relative path strings (listed to the model, never read) |
| `task_mandatory` | `true` for chapters |

`learn_only` / `direct_reference` cannot be represented in a plan; it stays on the ContextAsset and is applied by the code that calls the model.

## A.4 Job rules

| # | Rule |
|--:|---|
| J1 | The plan is derived from the Book Document and is **never parsed back**. Only `task_completed`, `audit_passed`, `audit_fail_reason`, `Job_Complete` and `Completion_Date` flow back (sync). |
| J2 | Plan files do not run Core's stage-0 validator (Core rejects `array` inside 104a). They are checked by the plan check **P** below. This is the only scoped exception in the standard. |
| J3 | A runner's output is **staging only**: `runs/<job slug>/<task id slug>.md` (task id lowercased, non-alphanumerics to `_`). It enters the book only through the gated ingest step. |
| J4 | Ingest: for each task that is `task_completed`, whose chapter is not yet `accepted`, and whose staged file exists: run the BookType gate; record a Generation (provider `jobrunner`); accepted or rejected as in W2; on failure set the task back to `task_completed = false`; sync; the caller commits. |
| J5 | No shell command is ever run for a book. A plan with a `test_cmd` column is not conforming; a legacy plan is read with `plan_normalize_legacy` (drops `Target_File` and an empty `test_cmd`, refuses a non-empty one). |
| J6 | Plan check **P**: `Records_Type` and the 11 fields exact; header set exact (keys starting `_` ignored) with the types and values above; `task_id` UUID and unique; `task_order` 1..N; brief non-empty; context and reference cell shapes; `Job_Complete` agrees with tasks; with the Book Document supplied, task ids and order equal its writable chapters. |

---

# Part B. Writing schema

## B.1 Files

| Artifact | Format | Location |
|---|---|---|
| Book Document | BEJSON **104db**, `Records_Type ["Book","Chapter","Generation","Export"]` | `books/<slug>.bks.bejson` |
| BookType | BEJSON **104**, `Records_Type ["BookType"]`, one row | `book_types/<slug>.bks-type.bejson` |
| Library entities | Author, Category, ContextAsset, RegistryEntry (schema defined; storage is the app's MFDB library) | app-defined |

Book Document: `Fields` = `Record_Type_Parent` + every Book, Chapter, Generation, Export field in registry order (68 columns), each carrying `"Record_Type_Parent": "<Entity>"`; no custom headers; exactly one Book row; rows are full width and null-padded; order: Book, Chapters by `chapter_order_index`, Generations oldest first, Exports. Read through a **field map**; never by column position. Strip whitespace from keys and strings at ingestion.

## B.2 Book (25 fields) · primary key `book_uuid`

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `book_uuid` | string | ● |  |
| 2 | `book_title_text` | string | ● |  |
| 3 | `book_subtitle_text` | string |  |  |
| 4 | `book_topic_text` | string | ● |  |
| 5 | `book_goal_text` | string |  |  |
| 6 | `book_booktype_uuid_fk` | string |  |  |
| 7 | `book_booktype_slug_text` | string | ● |  |
| 8 | `book_author_uuid_fk` | string |  |  |
| 9 | `book_author_name_text` | string | ● |  |
| 10 | `book_category_uuid_fk` | string |  |  |
| 11 | `book_category_name_text` | string |  |  |
| 12 | `book_plan_uuid_fk` | string |  |  |
| 13 | `book_language_text` | string | ● |  |
| 14 | `book_audience_text` | string |  |  |
| 15 | `book_summary_text` | string |  |  |
| 16 | `book_cover_path_text` | string |  |  |
| 17 | `book_tags_list` | array |  |  |
| 18 | `book_version_text` | string | ● |  |
| 19 | `book_status_text` | string | ● | `draft` · `complete` · `final` · `archived` |
| 20 | `book_chapter_count` | integer | ● |  |
| 21 | `book_word_count` | integer | ● |  |
| 22 | `book_content_sha256_text` | string |  |  |
| 23 | `book_schema_version_text` | string | ● |  |
| 24 | `book_created_at` | string | ● |  |
| 25 | `book_updated_at` | string | ● |  |

## B.3 Chapter (16 fields) · primary key `chapter_uuid`

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `chapter_uuid` | string | ● |  |
| 2 | `chapter_book_uuid_fk` | string | ● |  |
| 3 | `chapter_parent_uuid_fk` | string |  |  |
| 4 | `chapter_kind_text` | string | ● | `front` · `part` · `chapter` · `section` · `back` |
| 5 | `chapter_order_index` | integer | ● |  |
| 6 | `chapter_title_text` | string | ● |  |
| 7 | `chapter_brief_text` | string |  |  |
| 8 | `chapter_body_md` | string |  |  |
| 9 | `chapter_status_text` | string | ● | `planned` · `drafted` · `accepted` · `rejected` |
| 10 | `chapter_word_count` | integer | ● |  |
| 11 | `chapter_audit_enabled_flag` | boolean | ● |  |
| 12 | `chapter_audit_passed_flag` | boolean |  |  |
| 13 | `chapter_audit_fail_reason_text` | string |  |  |
| 14 | `chapter_generation_uuid_fk` | string |  |  |
| 15 | `chapter_created_at` | string | ● |  |
| 16 | `chapter_updated_at` | string | ● |  |

## B.4 Generation (16 fields) · primary key `generation_uuid`

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `generation_uuid` | string | ● |  |
| 2 | `generation_target_kind_text` | string | ● | `plan` · `chapter` |
| 3 | `generation_target_uuid_fk` | string | ● |  |
| 4 | `generation_provider_text` | string |  |  |
| 5 | `generation_model_text` | string |  |  |
| 6 | `generation_author_uuid_fk` | string |  |  |
| 7 | `generation_prompt_sha256_text` | string |  |  |
| 8 | `generation_temperature_value` | number |  |  |
| 9 | `generation_max_tokens_count` | integer |  |  |
| 10 | `generation_input_tokens_count` | integer |  |  |
| 11 | `generation_output_tokens_count` | integer |  |  |
| 12 | `generation_attempt_index` | integer | ● |  |
| 13 | `generation_outcome_text` | string | ● | `accepted` · `rejected` · `failed` · `cancelled` |
| 14 | `generation_error_code` | integer |  |  |
| 15 | `generation_started_at` | string | ● |  |
| 16 | `generation_finished_at` | string |  |  |

## B.5 Export (10 fields) · primary key `export_uuid`

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `export_uuid` | string | ● |  |
| 2 | `export_book_uuid_fk` | string | ● |  |
| 3 | `export_format_text` | string | ● | `md` · `md_zip` · `html` · `txt` · `json` · `bejson` |
| 4 | `export_renderer_text` | string | ● |  |
| 5 | `export_theme_text` | string |  |  |
| 6 | `export_path_text` | string | ● |  |
| 7 | `export_size_bytes_count` | integer |  |  |
| 8 | `export_sha256_text` | string | ● |  |
| 9 | `export_source_content_sha256_text` | string | ● |  |
| 10 | `export_created_at` | string | ● |  |

## B.6 BookType (19 fields, BEJSON 104) · primary key `booktype_uuid`

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `booktype_uuid` | string | ● |  |
| 2 | `booktype_slug_text` | string | ● |  |
| 3 | `booktype_name_text` | string | ● |  |
| 4 | `booktype_description_text` | string |  |  |
| 5 | `booktype_family_text` | string | ● | `nonfiction` · `technical` · `analysis` · `creative` |
| 6 | `booktype_plan_instruction_text` | string | ● |  |
| 7 | `booktype_chapter_identity_text` | string | ● |  |
| 8 | `booktype_outline_template_list` | array |  |  |
| 9 | `booktype_required_sections_list` | array |  |  |
| 10 | `booktype_min_chapters_count` | integer | ● |  |
| 11 | `booktype_max_chapters_count` | integer | ● |  |
| 12 | `booktype_default_chapters_count` | integer | ● |  |
| 13 | `booktype_min_words_per_chapter_count` | integer | ● |  |
| 14 | `booktype_audit_profile_text` | string | ● | `none` · `standard` · `strict` |
| 15 | `booktype_default_exports_list` | array |  |  |
| 16 | `booktype_is_builtin_flag` | boolean | ● |  |
| 17 | `booktype_schema_version_text` | string | ● |  |
| 18 | `booktype_created_at` | string | ● |  |
| 19 | `booktype_updated_at` | string | ● |  |

## B.7 Library entities

### Author (21)

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `author_uuid` | string | ● |  |
| 2 | `author_name_text` | string | ● |  |
| 3 | `author_email_text` | string |  |  |
| 4 | `author_website_text` | string |  |  |
| 5 | `author_github_text` | string |  |  |
| 6 | `author_bio_text` | string |  |  |
| 7 | `author_avatar_path_text` | string |  |  |
| 8 | `author_archetype_text` | string |  |  |
| 9 | `author_persona_text` | string |  |  |
| 10 | `author_system_instruction_text` | string |  |  |
| 11 | `author_tone_list` | array |  |  |
| 12 | `author_forbidden_topics_list` | array |  |  |
| 13 | `author_formality_text` | string | ● | `casual` · `neutral` · `formal` |
| 14 | `author_verbosity_text` | string | ● | `concise` · `balanced` · `expansive` |
| 15 | `author_creativity_value` | number | ● |  |
| 16 | `author_max_response_tokens_count` | integer | ● |  |
| 17 | `author_thinking_enabled_flag` | boolean | ● |  |
| 18 | `author_tools_list` | array |  |  |
| 19 | `author_is_deleted_flag` | boolean | ● |  |
| 20 | `author_created_at` | string | ● |  |
| 21 | `author_updated_at` | string | ● |  |

### Category (7)

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `category_uuid` | string | ● |  |
| 2 | `category_name_text` | string | ● |  |
| 3 | `category_slug_text` | string | ● |  |
| 4 | `category_badge_color_hex` | string | ● |  |
| 5 | `category_is_deleted_flag` | boolean | ● |  |
| 6 | `category_created_at` | string | ● |  |
| 7 | `category_updated_at` | string | ● |  |

### ContextAsset (9)

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `context_uuid` | string | ● |  |
| 2 | `context_original_file_name_text` | string | ● |  |
| 3 | `context_file_format_text` | string | ● | `txt` · `code` · `json` · `bejson` |
| 4 | `context_source_path_text` | string | ● |  |
| 5 | `context_size_bytes_count` | integer | ● |  |
| 6 | `context_sha256_text` | string | ● |  |
| 7 | `context_study_instruction_text` | string | ● | `learn_only` · `direct_reference` |
| 8 | `context_is_active_flag` | boolean | ● |  |
| 9 | `context_uploaded_at` | string | ● |  |

### RegistryEntry (9)

| # | Field | Type | Req | Values |
|--:|---|---|:-:|---|
| 1 | `registry_uuid` | string | ● |  |
| 2 | `registry_kind_text` | string | ● | `book` · `plan` · `booktype` · `author` · `category` · `template` · `schema` |
| 3 | `registry_name_text` | string | ● |  |
| 4 | `registry_slug_text` | string | ● |  |
| 5 | `registry_file_path_text` | string | ● |  |
| 6 | `registry_target_uuid_fk` | string |  |  |
| 7 | `registry_schema_version_text` | string | ● |  |
| 8 | `registry_created_at` | string | ● |  |
| 9 | `registry_updated_at` | string | ● |  |

## B.8 Enumerations

| Field | Allowed values |
|---|---|
| `book_status_text` | `draft` · `complete` · `final` · `archived` |
| `chapter_kind_text` | `front` · `part` · `chapter` · `section` · `back` |
| `chapter_status_text` | `planned` · `drafted` · `accepted` · `rejected` |
| `generation_target_kind_text` | `plan` · `chapter` |
| `generation_outcome_text` | `accepted` · `rejected` · `failed` · `cancelled` |
| `export_format_text` | `md` · `md_zip` · `html` · `txt` · `json` · `bejson` |
| `author_formality_text` | `casual` · `neutral` · `formal` |
| `author_verbosity_text` | `concise` · `balanced` · `expansive` |
| `context_file_format_text` | `txt` · `code` · `json` · `bejson` |
| `context_study_instruction_text` | `learn_only` · `direct_reference` |
| `registry_kind_text` | `book` · `plan` · `booktype` · `author` · `category` · `template` · `schema` |
| `booktype_family_text` | `nonfiction` · `technical` · `analysis` · `creative` |
| `booktype_audit_profile_text` | `none` · `standard` · `strict` |

Reserved, not valid yet: export formats `epub`, `docx`, `pdf`.

---

# Part C. Rules

## C.1 Field and value conventions

| # | Rule |
|--:|---|
| V1 | Names are `snake_case` with one entity prefix (`book_`, `chapter_`, `generation_`, `export_`, `author_`, `category_`, `booktype_`, `context_`, `registry_`). |
| V2 | Suffixes: `_uuid` key, `_uuid_fk` foreign key, `_at` UTC timestamp, `_text` string, `_md` Markdown, `_flag` boolean, `_count`/`_index` integer, `_value` number, `_list` array, `_path_text` relative path, `_sha256_text` lowercase hex, `_hex` colour. |
| V3 | Absence is `null`; an empty string is an error (513). |
| V4 | Timestamps are exactly `YYYY-MM-DDTHH:MM:SSZ` (UTC). |
| V5 | UUIDs are canonical lowercase hyphenated. Keys are UUIDv4, or UUIDv5 where a stable id is needed (`uuid5(book_uuid, "part:" + title)` for parts). |
| V6 | Stored paths are relative to the project root, use `/`, never contain `..`, a drive letter or a leading slash. |
| V7 | Foreign keys end `_fk`, point at the parent's UUID and never dangle. Generations are append-only history. |
| V8 | Body normalisation: `\r\n` and `\r` to `\n`; trailing whitespace of the whole body stripped. |
| V9 | Word count: remove fenced code blocks, count whitespace-separated tokens. |
| V10 | Derived values are recomputed on every commit and never trusted from callers: `chapter_word_count`, `book_chapter_count` (nodes that are not `part`), `book_word_count`, `book_content_sha256_text`. |
| V11 | `book_schema_version_text` and `booktype_schema_version_text` are `bks-1.0.0`; readers accept any `bks-1.*`. |

**Content hash (exact):**

```
text  = "BKS1\n" + NFC(book_title_text) + "\n"
for each Chapter row, ALL kinds including parts, in chapter_order_index order:
    text += "\x1e" + chapter_uuid + "\x1f" + (chapter_parent_uuid_fk or "") + "\x1f" + chapter_kind_text
          + "\x1f" + NFC(chapter_title_text) + "\x1f" + NFC(normalise(chapter_body_md) or "") + "\n"
book_content_sha256_text = lowercase hex SHA-256 of UTF-8(text)
```

Test vector 1 (the kit's worked example) = `87f04e7df99c0984309d5c920a4af92bacb8fccc4a51c37533865c8c301b29bd`. Not hashed: status, version, timestamps, briefs, audit fields, generations, exports.

## C.2 Outline and status

- `chapter_order_index` is one global reading order 1..N over all rows (parts included).
- Parents: `part`, `front`, `back` have none; `chapter` has none or a `part`; `section` has a `chapter`. The parent graph is a tree (checked with Core's list validator on `id`/`parent_id`). Parts are structure only and are never written.
- Chapter status: `planned` (no body) → `drafted` (body, no gate) → `accepted` (body; if audit enabled the gate passed; points at an accepted Generation for this chapter) or `rejected` (body kept, `audit_passed = false`, reason present). Parts are always `accepted` with no body.
- Book status: `draft` (no Export rows allowed) → `complete` (every writable node accepted) → `final` (hash required and correct) → `archived`.

## C.3 Write rules

| # | Rule |
|--:|---|
| W1 | The Book Document, with its full outline, exists before the first model call. |
| W2 | Every model attempt is a Generation. The gate runs in process on the staged text. Pass: `accepted`. Fail: `rejected` with the reason. A failed or empty attempt never overwrites an accepted body; a provider error is a `failed` Generation and leaves the chapter unchanged. |
| W3 | One commit path: recompute derived values, validate (C3; C4 when Export rows exist), lock, atomic replace. An invalid document is never written. |
| W4 | Resume needs only the Book Document: the next chapter is the first writable node not `accepted`. |
| W5 | The Book Document wins; plans and publications are rewritten from it, never the reverse. |
| W6 | Plans, `runs/` files and exports are derived and may be rebuilt. |
| W7 | Editing a `complete` or `final` book sets it to `draft`, bumps the patch version and deletes its Export rows. |
| W8 | Writers take the file lock and write atomically. There is no second writer. |

## C.4 Gates (in-process, declarative, never a shell)

| Rule | Meaning |
|---|---|
| `min_words` / `max_words` | word count at least / at most N |
| `must_include` | list of Markdown heading texts that must appear (case-insensitive) |
| `no_placeholders` | fails on `TODO`, `TBD`, `FIXME`, `lorem ipsum`, `[insert ...]`, `[...]` |
| `md_wellformed` | code fences balanced |

Profiles: `none` (no gate), `standard` (`min_words` + `no_placeholders`), `strict` (standard + `md_wellformed` + `must_include` the type's required sections). An unknown rule or profile is refused (537). `chapter_audit_enabled_flag = false` skips the gate.

## C.5 BookType rules

`1 <= min_chapters <= default_chapters <= max_chapters`; `required_sections` and `default_exports` are lists of non-empty strings; each default export is a valid export format; each outline item has a non-empty `title` and a `kind` of `front`, `chapter`, `section` or `back` (optional `brief`, `part`); `booktype_plan_instruction_text` contains `{chapter_count}`. Chapter limits apply when a plan is made. The outline template is a starting point (truncated, never padded).

## C.6 Render and export rules

| # | Rule |
|--:|---|
| R1 | Deterministic: same document and options give identical bytes. |
| R2 | A renderer reads only the Book Document, which must conform at C3. |
| R3 | A `draft` book is refused (539) unless a preview is requested; a preview is marked DRAFT and writes no Export row. |
| R4 | The renderer owns headings and numbering; a leading body heading that duplicates the node title is dropped; body headings are shifted under their node. |
| R5 | HTML escapes all text before adding markup; only headings, paragraphs, lists, blockquotes, fenced code, bold, italic and inline code are rendered; links are never live; no scripts, no external resources. |
| R6 | An export is rendered, written atomically, recorded as an Export row and the book committed at C4 as one operation. Re-exporting the same format and path replaces its row. An app may pass a `slug` to keep exports of same-titled books apart. |

Formats: `md`, `md_zip` (`<slug>/book.bks.bejson`, `metadata.json`, `chapters/NNN-title.md`), `html`, `txt`, `json`, `bejson`. Export path `exports/<slug>/<slug><ext>`.

## C.7 Publish rules (added in 1.0.2, from the CMS audit)

These apply to any application that publishes book content to a live target (a CMS page, a site, a feed).

| # | Rule |
|--:|---|
| PUB1 | Publish only from a book whose writable nodes are **all `accepted`**. Partial, drafted or rejected content is never published. A preview of unfinished content must be marked as unpublishable. |
| PUB2 | Model-generated and edited text is **untrusted**. Before it is stored or converted for a live target: escape raw HTML outside code, limit link and image destinations to `http`, `https`, `mailto`, anchors and relative paths (everything else becomes `#`), and re-check the converted output for blocked tags, event-handler attributes and `javascript:`/`vbscript:`/`data:` URLs, refusing to publish if any remain. The Book Document keeps the original text. |
| PUB3 | **Finalize and export (C4) before touching the live target.** Any failure aborts with an error and leaves the target unchanged; a failure must never be only logged. |
| PUB4 | Published content derives only from the book's accepted bodies. An override (text not produced by the book) is allowed only if it is escaped under PUB2 and recorded as `approved_override`. |
| PUB5 | When an accepted part changes after publication, the publication state becomes `stale`. |
| PUB6 | A provider failure never reuses a BKS error code in `generation_error_code`; use `null` or an application code (550 to 579). |

## C.8 Conformance levels

| Level | Checks |
|---|---|
| C1 Structure | Core validator passes; `Fields`/`Records_Type` equal the registry; one Book row; schema version; required fields; enumerations; timestamps, UUIDs, relative paths; no empty strings |
| C2 Integrity | keys unique; foreign keys resolve; order 1..N; tree; parent kinds; derived values correct |
| C3 Lifecycle | statuses agree with data; audit gate passed for accepted audited chapters; accepted chapters have an accepted Generation; hash correct (required when final) |
| C4 Release | exports only on complete, final or archived books; no export rendered from older content |
| P Plan | A.4 rule J6 |
| L Library file | Core validator; BEJSON 104 with the registry columns; per-row rules; C.5 |

Levels stack. Everything a system stores passes C3 (C4 once it has exports).

## C.9 Error codes (500 to 549; 550 to 579 are reserved for applications)

| Code | Name | Meaning |
|--:|---|---|
| 500 | `E_BKS_STRUCTURE` | Core validator rejected the document |
| 501 | `E_BKS_SCHEMA_MISMATCH` | Fields/Records_Type differ from the registry |
| 502 | `E_BKS_VERSION_UNSUPPORTED` | schema version not bks-1.* |
| 503 | `E_BKS_BOOK_COUNT` | not exactly one Book row |
| 510 | `E_BKS_REQUIRED_NULL` | required field is null |
| 511 | `E_BKS_ENUM_INVALID` | value outside its enumeration |
| 512 | `E_BKS_TIMESTAMP_INVALID` | not a UTC timestamp |
| 513 | `E_BKS_EMPTY_STRING` | empty string stored (use null) |
| 514 | `E_BKS_UUID_INVALID` | not a canonical UUID |
| 515 | `E_BKS_PATH_INVALID` | not a relative forward-slash path |
| 520 | `E_BKS_PK_DUPLICATE` | duplicate primary key |
| 521 | `E_BKS_FK_DANGLING` | foreign key does not resolve |
| 522 | `E_BKS_ORDER_INVALID` | order is not 1..N |
| 523 | `E_BKS_OUTLINE_INVALID` | parent graph is not a tree |
| 524 | `E_BKS_PARENT_KIND` | kind does not fit parent kind |
| 525 | `E_BKS_DERIVED_MISMATCH` | derived value wrong |
| 526 | `E_BKS_STATUS_INCONSISTENT` | status contradicts data |
| 527 | `E_BKS_GATE_NOT_PASSED` | audited chapter accepted without a passed gate |
| 528 | `E_BKS_PROVENANCE_MISSING` | accepted chapter lacks an accepted Generation |
| 529 | `E_BKS_HASH_MISMATCH` | content hash wrong or missing on a final book |
| 530 | `E_BKS_EXPORT_NOT_ALLOWED` | Export row on a book that may not have exports |
| 531 | `E_BKS_EXPORT_STALE` | Export rendered from older content |
| 532 | `E_BKS_PLAN_NOT_JOBTASK` | plan is not the 11-field JobTask schema |
| 533 | `E_BKS_PLAN_HEADER` | plan header missing/extra/mistyped, or Job_Type/Subtype not writing/book |
| 535 | `E_BKS_PLAN_CELL_SHAPE` | plan context/reference cell not an array of runner shapes |
| 536 | `E_BKS_PLAN_LINK` | plan tasks do not match the book's writable chapters |
| 537 | `E_BKS_GATE_UNKNOWN` | unknown gate rule or profile |
| 538 | `E_BKS_IMPORT_UNSUPPORTED` | import source unsupported (reserved) |
| 539 | `E_BKS_RENDER_FAILED` | renderer refused or failed |
| 540 | `E_BKS_MIGRATION_FAILED` | migration failed (reserved) |
| 541 | `E_BKS_BOOKTYPE_LIMITS` | BookType limits/outline/exports inconsistent |
| 534 | *retired* | formerly `E_BKS_TEST_CMD_FORBIDDEN`; never reused |

---

*Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton*
