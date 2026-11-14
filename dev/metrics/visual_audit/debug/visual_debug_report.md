# Playwright Visual Debug & State Interaction Report

- **Target URL**: `http://127.0.0.1:8080/index.html`
- **Status**: `PASS`
- **Horizontal Overflow**: `False` (Width: `1280px` / Win: `1280px`)
- **Sidebar List Margin Top**: `32px` (Target: `32px` [PASS])
- **Layer Z-Index Verification**:
  - Drawer: `z-index: 96` (Layer 3: 3*32 = 96)
  - Header: `z-index: 128` (Layer 4: 4*32 = 128)
  - Dock Strip: `z-index: 128` (Layer 4: 4*32 = 128)
  - Modal Dialog: `z-index: 160` (Layer 5: 5*32 = 160)
- **3D Viewport Telemetry**:
  - Exploded Stage Transform: `rotateX(52deg) rotateY(-28deg) rotateZ(0deg)`
  - Layer 5 Transform: `translateZ(400px) translateY(-200px)`
  - HUD Total Dispersion: `Total Spread: 400px`
- **Console Exceptions Count**: `0`

## Captured State Screenshots

- **01_initial_series1**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/01_initial_series1.png` — Test Series 1 MFDB Federation and 254 entities overview
- **02_sidebar_open**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/02_sidebar_open.png` — Sidebar navigation open with verified 32px top margin (1 quantized row)
- **03_series2_sql**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/03_series2_sql.png` — Test Series 2 BEJSON 105 vs SQLite point queries and token comparison
- **04_series3_stress**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/04_series3_stress.png` — Test Series 3 High-scale stress: 25k (5 entities) and 60k (3 entities)
- **05_series4_3d_viewport**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/05_series4_3d_viewport.png` — Test Series 4 Canonical 6-layer 3D vertical axis viewport demonstration
- **06_3d_exploded_2.5x**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/06_3d_exploded_2.5x.png` — Exploded 3D stage with 2.5x Z-separation (400px dispersion)
- **07_inspector_hud_modal**: `/storage/emulated/0/Admin/Libraries/libraries_105/dev/metrics/visual_audit/debug/07_inspector_hud_modal.png` — Spatial Inspector HUD modal open with verified z-index: 160
