# lib_bejson_Scaffold

- **File:** Lib_PY/Scaffold/README.md
- **Purpose:** Deploy rebuild / prebuilt master or slave nodes, reserve and bind Z-space, manage federation links (BEJSON 105 / MFDB v1.40).
- **VERSION:** 1.0.0
- **RELATIONAL_ID:** af9f6c80-f138-4386-b5b4-bb8c4ce298c0
- **Author:** Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton

Imports `lib_bejson_Core` (unmodified) and `lib_bejson_Taxonomies`. Calls exactly one Core private helper, `_bejson_core_invalidate_cache`, as granted in `clarification.md` §5.6.

## Modules

| Module | Role |
|---|---|
| `lib_bejson_Scaffold_z_space_allocator` | Reserve trailing `_slot` columns; bind a slot by renaming it (uuid and position unchanged) |
| `lib_bejson_Scaffold_deployment_registry` | Register / look up deployments; set manifest `Network_Role` |
| `lib_bejson_Scaffold_federation_bridge` | Create/bind/resolve/tear down links; build and push link config over Core's drop-zone |
| `lib_bejson_Scaffold_rebuild_master` | Deploy a node rebuilt from a taxonomy (root or a variant) |
| `lib_bejson_Scaffold_prebuilt_master` | Capture a snapshot; deploy a prebuilt node (master or slave) from it |

## Public API (all `bejson_scaffold_*`)

| Function | Purpose |
|---|---|
| `deploy_rebuild` / `deploy_master_rebuild` / `deploy_slave_rebuild` | New node from scratch; optional variant taxonomy |
| `capture_snapshot(source_manifest, snapshot_dir)` | Copy a DB, strip deployments/links/ConnectedSlave rows, audit |
| `deploy_prebuilt` / `deploy_master_prebuilt` / `deploy_slave_prebuilt` | Node from a snapshot; `taxonomy_ref` required if the snapshot holds more than one taxonomy |
| `reserve_z_space_slot(manifest, entity, taxonomy_ref, slot_count, fk_target_entity, fk_on_delete)` | Append unbound slots; all-or-nothing with rollback |
| `bind_z_space_slot(manifest, entity, slot_field_uuid, bound_name)` | Compliant rename; no row rewritten |
| `list_z_space` / `find_slot` | Reservations with the slot's current name |
| `register_deployment` / `get_deployment` / `list_deployments` / `set_deployment_active` / `set_network_role` | Deployment rows |
| `create_federation_link(manifest, master_ref, slave_ref)` | Roles checked; match kind (`identical`/`variant`) computed |
| `bind_federation_link(manifest, node_ref, link_uuid)` | Binds the slot if needed, writes the link UUID |
| `resolve_federation_link` / `get_federation_link` / `teardown_federation_link` | Follow the slot by `field_uuid`; teardown nulls both slots |
| `build_link_config` / `push_link_config` / `read_link_config` | 104a transport document via Core `mfdb_federation_push_config` |

Deployment kinds: strategy `rebuild` or `prebuilt`; role `master` or `slave`. All four combinations are legal.

## Not implemented in this release

Applying a pushed link config on the slave (mirroring the link and node rows with preserved UUIDs into the slave's own database). Core's public add-record call always generates a new `record_uuid`, so this needs a decision on how UUID-preserving inserts should be done.

## Tests

`python3 Lib_PY/Scaffold/tests/test_scaffold.py` (28 tests).
