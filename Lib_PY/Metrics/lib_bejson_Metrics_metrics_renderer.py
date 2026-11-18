#!/usr/bin/env python3
"""
Name:          lib_bejson_Metrics_metrics_renderer.py
Description:   Tri-Color (#000000/#FFFFFF/#DE2626) SVG & HTML5 Canvas Visual Showcase renderer using stacked (Label -> Line Break -> Full-Width Bar) layout that fits mobile and desktop screens.
Version:       1.3.0
Date Created:  2026-11-18
Author Credit: Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID: lib-bejson-metrics-renderer-v130-20261118
License:       PolyForm-Noncommercial-1.0.0
"""

from __future__ import annotations

import html
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10+ is required.")

_CORE_DIR: Path = Path(__file__).resolve().parent.parent / "Core"
if str(_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_CORE_DIR))

from lib_bejson_Core_bejson_core import bejson_core_get_field_map
from lib_bejson_Metrics_metrics_errors import E_METRICS_RENDER_FAILED, MetricsLibraryError

LOGGER_INSTANCE = logging.getLogger("lib_bejson_Metrics.renderer")


def _slugify_id(raw_text: str) -> str:
    """Normalize arbitrary text into a clean DOM id token."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_text.strip().lower()).strip("-")
    return cleaned or "item"


def render_tri_color_bar_svg(
    chart_title: str,
    bars: List[Tuple[str, float, str]],
    width_px: int = 680,
    height_px: int = 320,
    svg_id: str = "svg-metric-chart",
) -> str:
    """
    Render a Tri-Color (#000000, #FFFFFF, #DE2626) stacked bar SVG:
    Line 1: Full-width Label (no collision)
    Line 2 (below): Proportional Bar Line + Value label
    """
    if not bars:
        raise MetricsLibraryError("Cannot render empty bar dataset.", error_code=E_METRICS_RENDER_FAILED)

    safe_svg_id = _slugify_id(svg_id)
    max_val = max((val for _, val, _ in bars), default=1.0) or 1.0
    pad_x = 18
    value_gutter = 145
    top_margin = 68
    bar_full_width = max(140, width_px - (pad_x * 2) - value_gutter)
    row_step = 56
    computed_height = max(height_px, top_margin + len(bars) * row_step + 20)

    svg_parts: List[str] = [
        f'<svg id="{safe_svg_id}" xmlns="http://www.w3.org/2000/svg" width="100%" height="{computed_height}" viewBox="0 0 {width_px} {computed_height}">',
        f'  <rect id="{safe_svg_id}-bg" width="{width_px}" height="{computed_height}" fill="#000000"/>',
        f'  <text id="{safe_svg_id}-title" x="{pad_x}" y="34" fill="#FFFFFF" font-family="monospace" font-size="16" font-weight="bold">{html.escape(chart_title)}</text>',
        f'  <line id="{safe_svg_id}-divider" x1="{pad_x}" y1="46" x2="{width_px - pad_x}" y2="46" stroke="#DE2626" stroke-width="2"/>',
    ]

    for idx, (label_text, val, unit_str) in enumerate(bars):
        y_top = top_margin + idx * row_step
        bar_y = y_top + 8
        bar_w = max(6, int((val / max_val) * bar_full_width))
        fill_color = "#DE2626" if idx % 2 == 0 else "#FFFFFF"
        row_id = f"{safe_svg_id}-row-{idx}"
        val_formatted = f"{val:,.2f} {unit_str}"
        svg_parts.append(
            f'  <g id="{row_id}">'
            f'<text id="{row_id}-label" x="{pad_x}" y="{y_top}" fill="#FFFFFF" font-family="monospace" font-size="13">{html.escape(str(label_text))}</text>'
            f'<rect id="{row_id}-track" x="{pad_x}" y="{bar_y}" width="{bar_full_width}" height="18" fill="#161618"/>'
            f'<rect id="{row_id}-bar" x="{pad_x}" y="{bar_y}" width="{bar_w}" height="18" fill="{fill_color}"/>'
            f'<text id="{row_id}-value" x="{pad_x + bar_full_width + 10}" y="{bar_y + 14}" fill="#FFFFFF" font-family="monospace" font-size="12" font-weight="bold">{html.escape(val_formatted)}</text>'
            f"</g>"
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def build_scrollable_dashboard_document(
    page_title: str,
    panels_spec: List[Dict[str, Any]],
    kpi_cards: List[Dict[str, str]] | None = None,
    test_table_rows: List[Dict[str, Any]] | None = None,
) -> str:
    """
    Build a unified Tri-Color HTML5 Visual Showcase document:
    - Stacked bar layout: Line 1 = Label -> Line break -> Line 2 = Bar Line + Value -> Repeat.
    - Fits mobile (390px) and desktop (1280px) screens naturally while keeping overflow-x: auto containers.
    - Mandatory unique DOM id attributes on every structural and interactive node.
    """
    dock_links_html: List[str] = []
    panels_html: List[str] = []
    js_datasets: Dict[str, Dict[str, Any]] = {}

    if kpi_cards:
        dock_links_html.append('<a id="dock-link-kpi-summary" class="dock-chip" href="#section-kpi-summary">KPI Summary</a>')

    for p_spec in panels_spec:
        slug = _slugify_id(p_spec["slug"])
        heading = html.escape(p_spec["heading"])
        subtitle = html.escape(p_spec.get("subtitle", ""))
        render_mode = p_spec.get("mode", "canvas")
        bars_list = p_spec["bars"]
        dock_links_html.append(
            f'<a id="dock-link-{slug}" class="dock-chip" href="#panel-{slug}">{heading}</a>'
        )

        if render_mode == "svg":
            stage_inner = p_spec["svg_markup"]
        else:
            canvas_id = f"canvas-{slug}"
            canvas_height = max(180, 68 + len(bars_list) * 56 + 16)
            js_datasets[canvas_id] = {
                "title": p_spec.get("chart_title", p_spec["heading"]),
                "height": canvas_height,
                "items": [{"label": str(l), "value": float(v), "unit": str(u)} for l, v, u in bars_list],
            }
            stage_inner = f'<canvas id="{canvas_id}" height="{canvas_height}"></canvas>'

        summaries_list: List[str] = p_spec.get("summaries", [])
        summary_block_html = ""
        if summaries_list:
            li_items = "\n".join(
                f'          <li id="summary-item-{slug}-{s_idx}" class="summary-bullet">{html.escape(s_text)}</li>'
                for s_idx, s_text in enumerate(summaries_list)
            )
            summary_block_html = f"""      <div id="summary-box-{slug}" class="metric-narrative-summary">
        <span id="summary-heading-{slug}" class="summary-heading">Data Summary</span>
        <ul id="summary-list-{slug}" class="summary-list">
{li_items}
        </ul>
      </div>"""

        panels_html.append(
            f"""    <section id="panel-{slug}" class="metric-panel">
      <div id="panel-header-{slug}" class="panel-header">
        <h2 id="panel-title-{slug}">{heading}</h2>
        <span id="panel-subtitle-{slug}" class="panel-subtitle">{subtitle}</span>
      </div>
      <div id="scroll-wrap-{slug}" class="graph-scroll-viewport" tabindex="0" role="region" aria-label="{heading}">
        <div id="stage-{slug}" class="graph-intrinsic-stage">
          {stage_inner}
        </div>
      </div>
{summary_block_html}
    </section>"""
        )

    kpi_section_html = ""
    if kpi_cards:
        cards_html: List[str] = []
        for c_idx, card in enumerate(kpi_cards):
            cid = _slugify_id(card.get("id", f"kpi-{c_idx}"))
            accent_cls = "kpi-value-accent" if c_idx % 2 == 0 else "kpi-value-main"
            cards_html.append(
                f"""      <article id="kpi-card-{cid}" class="kpi-card">
        <span id="kpi-label-{cid}" class="kpi-label">{html.escape(card["label"])}</span>
        <strong id="kpi-value-{cid}" class="{accent_cls}">{html.escape(card["value"])}</strong>
        <span id="kpi-detail-{cid}" class="kpi-detail">{html.escape(card["detail"])}</span>
      </article>"""
            )
        kpi_section_html = (
            '    <section id="section-kpi-summary" class="kpi-grid">\n'
            + "\n".join(cards_html)
            + "\n    </section>"
        )

    table_section_html = ""
    if test_table_rows:
        dock_links_html.append('<a id="dock-link-test-matrix" class="dock-chip" href="#panel-test-matrix">Test Matrix</a>')
        tr_list: List[str] = []
        for r_idx, r_obj in enumerate(test_table_rows):
            status_str = str(r_obj["status"]).upper()
            badge_cls = "badge-pass" if status_str == "PASS" else "badge-fail"
            tr_list.append(
                f"""              <tr id="test-row-{r_idx}">
                <td id="test-row-{r_idx}-suite">{html.escape(str(r_obj["suite"]))}</td>
                <td id="test-row-{r_idx}-name">{html.escape(str(r_obj["name"]))}</td>
                <td id="test-row-{r_idx}-cat">{html.escape(str(r_obj["category"]))}</td>
                <td id="test-row-{r_idx}-status"><span id="test-row-{r_idx}-badge" class="status-badge {badge_cls}">{html.escape(status_str)}</span></td>
                <td id="test-row-{r_idx}-ms" class="num-cell">{float(r_obj["duration_ms"]):.2f} ms</td>
              </tr>"""
            )
        table_section_html = f"""    <section id="panel-test-matrix" class="metric-panel">
      <div id="panel-header-test-matrix" class="panel-header">
        <h2 id="panel-title-test-matrix">Automated Test Execution Matrix</h2>
        <span id="panel-subtitle-test-matrix" class="panel-subtitle">{len(test_table_rows)} Verified Cases</span>
      </div>
      <div id="scroll-wrap-test-matrix" class="graph-scroll-viewport" tabindex="0" role="region" aria-label="Test Execution Matrix">
        <div id="stage-test-matrix" class="graph-intrinsic-stage">
          <table id="table-test-matrix" class="metrics-table">
            <thead id="thead-test-matrix">
              <tr id="tr-head-test-matrix">
                <th id="th-suite">Suite</th>
                <th id="th-test">Test Case</th>
                <th id="th-category">Domain</th>
                <th id="th-status">Status</th>
                <th id="th-duration" class="num-cell">Latency</th>
              </tr>
            </thead>
            <tbody id="tbody-test-matrix">
{chr(10).join(tr_list)}
            </tbody>
          </table>
        </div>
      </div>
    </section>"""

    dock_joined = "\n    ".join(dock_links_html)
    panels_joined = "\n".join(p for p in [kpi_section_html, *panels_html, table_section_html] if p)
    data_json = json.dumps(js_datasets)

    return f"""<!DOCTYPE html>
<html id="html-root" lang="en">
<head id="head-root">
  <meta id="meta-charset" charset="UTF-8">
  <meta id="meta-viewport" name="viewport" content="width=device-width, initial-scale=1.0">
  <title id="doc-title">{html.escape(page_title)}</title>
  <style id="core-styles">
    :root {{
      --bg-void: #000000;
      --bg-panel: #111111;
      --bg-elevated: #161618;
      --bg-chip: #1F1F23;
      --fg-main: #FFFFFF;
      --accent-red: #DE2626;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: 100%;
      max-width: 100vw;
      overflow-x: hidden;
      background: var(--bg-void);
      color: var(--fg-main);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    #app-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 56px;
      padding: 0 16px;
      background: var(--bg-panel);
      border-bottom: 2px solid var(--accent-red);
    }}
    .header-icon-btn {{
      width: 40px;
      height: 40px;
      background: var(--bg-chip);
      color: var(--fg-main);
      border: none;
      font-size: 18px;
      font-weight: bold;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    #app-title {{
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }}
    #overflow-dock-strip {{
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      overflow-y: hidden;
      gap: 10px;
      padding: 10px 16px;
      background: var(--bg-elevated);
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
      scrollbar-color: var(--accent-red) var(--bg-panel);
    }}
    .dock-chip {{
      flex: 0 0 auto;
      padding: 6px 14px;
      background: var(--bg-chip);
      color: var(--fg-main);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
    }}
    .dock-chip:hover {{ background: var(--accent-red); }}
    #main-content {{
      width: 100%;
      max-width: 1280px;
      margin: 0 auto;
      padding: 18px 14px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
    }}
    .kpi-card {{
      background: var(--bg-panel);
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      border-left: 4px solid var(--accent-red);
    }}
    .kpi-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; }}
    .kpi-value-accent {{ font-size: 16px; line-height: 1.35; color: var(--accent-red); }}
    .kpi-value-main {{ font-size: 16px; line-height: 1.35; color: var(--fg-main); }}
    .kpi-detail {{ font-size: 11px; line-height: 1.4; background: var(--bg-elevated); padding: 4px 8px; }}
    .metric-panel {{
      width: 100%;
      background: var(--bg-panel);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .panel-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 8px;
      padding-bottom: 8px;
      border-bottom: 2px solid var(--accent-red);
    }}
    .panel-header h2 {{ font-size: 15px; color: var(--fg-main); }}
    .panel-subtitle {{ font-size: 11px; background: var(--bg-chip); padding: 3px 8px; }}
    .graph-scroll-viewport {{
      width: 100%;
      max-width: 100%;
      overflow-x: auto;
      overflow-y: hidden;
      background: var(--bg-elevated);
      padding: 10px;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: thin;
      scrollbar-color: var(--accent-red) var(--bg-void);
    }}
    .graph-intrinsic-stage {{
      width: 100%;
      min-width: 100%;
      display: block;
    }}
    .graph-intrinsic-stage canvas,
    .graph-intrinsic-stage svg {{
      width: 100%;
      height: auto;
      display: block;
      background: var(--bg-void);
    }}
    .metric-narrative-summary {{
      background: var(--bg-elevated);
      padding: 12px 14px;
      border-left: 3px solid var(--accent-red);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .summary-heading {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent-red);
    }}
    .summary-list {{
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 12px;
      line-height: 1.45;
      color: var(--fg-main);
    }}
    .summary-bullet::before {{
      content: "▸ ";
      color: var(--accent-red);
      font-weight: bold;
    }}
    .metrics-table {{
      width: 100%;
      min-width: 620px;
      border-collapse: collapse;
      background: var(--bg-void);
      font-size: 12px;
    }}
    .metrics-table th, .metrics-table td {{
      padding: 8px 12px;
      text-align: left;
      white-space: nowrap;
    }}
    .metrics-table thead tr {{ background: var(--bg-chip); border-bottom: 2px solid var(--accent-red); }}
    .metrics-table tbody tr:nth-child(even) {{ background: var(--bg-panel); }}
    .metrics-table tbody tr:nth-child(odd) {{ background: var(--bg-elevated); }}
    .num-cell {{ text-align: right; white-space: nowrap; }}
    .status-badge {{
      display: inline-block;
      padding: 2px 8px;
      font-weight: 700;
      font-size: 11px;
      white-space: nowrap;
    }}
    .badge-pass {{ background: var(--accent-red); color: var(--fg-main); }}
    .badge-fail {{ background: var(--fg-main); color: var(--bg-void); }}
    #app-footer {{
      margin-top: 12px;
      padding: 16px;
      background: var(--bg-panel);
      font-size: 11px;
      text-align: center;
    }}
  </style>
</head>
<body id="body-root">
  <header id="app-header">
    <button id="nav-hamburger-btn" class="header-icon-btn" type="button" aria-label="Menu">&#9776;</button>
    <h1 id="app-title">{html.escape(page_title)}</h1>
    <button id="nav-settings-btn" class="header-icon-btn" type="button" aria-label="Settings">&#9881;</button>
  </header>
  <nav id="overflow-dock-strip" aria-label="Section Navigation">
    {dock_joined}
  </nav>
  <main id="main-content">
{panels_joined}
  </main>
  <footer id="app-footer">
    <span id="footer-credit">Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton · PolyForm-Noncommercial-1.0.0</span>
  </footer>
  <script id="graph-renderer-script">
    const GRAPH_DATASETS = {data_json};
    function renderStackedCanvasBars(canvasId, cfg) {{
      const canvasEl = document.getElementById(canvasId);
      if (!canvasEl || !cfg || !cfg.items || !cfg.items.length) return;
      const stageW = Math.max(300, canvasEl.parentElement.clientWidth || 680);
      canvasEl.width = stageW;
      canvasEl.height = cfg.height || (68 + cfg.items.length * 56 + 16);
      const ctx = canvasEl.getContext('2d');
      const W = canvasEl.width, H = canvasEl.height;
      const padX = 14;
      const valGutter = 128;
      const barFullW = Math.max(100, W - padX * 2 - valGutter);

      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, W, H);

      ctx.fillStyle = '#FFFFFF';
      ctx.font = 'bold 13px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(cfg.title || '', padX, 28);

      ctx.fillStyle = '#DE2626';
      ctx.fillRect(padX, 40, W - padX * 2, 2);

      const maxVal = Math.max(...cfg.items.map(i => i.value)) || 1;
      const topMargin = 64, rowStep = 56;

      cfg.items.forEach((item, idx) => {{
        const yLabel = topMargin + idx * rowStep;
        const yBar = yLabel + 8;
        const barW = Math.max(6, Math.floor((item.value / maxVal) * barFullW));
        const valText = item.value.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + ' ' + item.unit;

        // Line 1: Full-width Label (no collision with value)
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '12px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(item.label, padX, yLabel);

        // Line 2 (below): Bar track + bar fill + value at right of bar
        ctx.fillStyle = '#161618';
        ctx.fillRect(padX, yBar, barFullW, 18);
        ctx.fillStyle = idx % 2 === 0 ? '#DE2626' : '#FFFFFF';
        ctx.fillRect(padX, yBar, barW, 18);

        ctx.fillStyle = '#FFFFFF';
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(valText, padX + barFullW + 8, yBar + 13);
      }});
    }}
    function renderAllCanvases() {{
      Object.keys(GRAPH_DATASETS).forEach(cid => renderStackedCanvasBars(cid, GRAPH_DATASETS[cid]));
    }}
    renderAllCanvases();
    window.addEventListener('resize', renderAllCanvases);
  </script>
</body>
</html>
"""


def render_metrics_dashboard_html(
    ledger_doc: Dict[str, Any],
    output_html_path: Path,
    svg_export_dir: Path | None = None,
) -> Path:
    """Render an interactive Tri-Color HTML5 Canvas + SVG metrics dashboard with stacked bar lines."""
    fmap = bejson_core_get_field_map(ledger_doc)
    rows = ledger_doc.get("Values", [])

    ops_bars: List[Tuple[str, float, str]] = []
    ingest_bars: List[Tuple[str, float, str]] = []
    token_bars: List[Tuple[str, float, str]] = []
    latency_rss_bars: List[Tuple[str, float, str]] = []
    seen_rss: set[str] = set()

    for row in rows:
        series = str(row[fmap["series_id"]])
        suite = str(row[fmap["suite_name"]])
        mcat = str(row[fmap["metric_category"]])
        pval = float(row[fmap["primary_value"]])
        bval = float(row[fmap["baseline_value"]])
        unit = str(row[fmap["unit"]])
        rss = float(row[fmap["peak_rss_mb"]])

        if mcat == "throughput":
            if unit == "ops/sec":
                ops_bars.append((f"{series} · {suite}", pval / 1_000_000.0, "M ops/s"))
                if bval > 0:
                    ops_bars.append((f"{series} · SQLite Baseline", bval / 1_000_000.0, "M ops/s"))
            else:
                ingest_bars.append((f"{series} · {suite}", pval / 1000.0, "k rec/s"))
        elif mcat == "tokens":
            token_bars.append((f"{series} · BEJSON 105", pval / 1000.0, "k tokens"))
            if bval > 0:
                token_bars.append((f"{series} · JSON Baseline", bval / 1000.0, "k tokens"))
        elif mcat == "latency":
            latency_rss_bars.append((f"{series} · Integrity Verify Gate", pval, unit))

        if series not in seen_rss and rss > 0:
            seen_rss.add(series)
            latency_rss_bars.append((f"{series} · Peak RSS", rss, "MB"))

    ops_bars = ops_bars or [("none", 0.0, "M ops/s")]
    ingest_bars = ingest_bars or [("none", 0.0, "k rec/s")]
    token_bars = token_bars or [("none", 0.0, "k tokens")]
    latency_rss_bars = latency_rss_bars or [("none", 0.0, "MB")]

    ops_svg = render_tri_color_bar_svg("Point Lookup & Cell Access (M ops/s)", ops_bars, svg_id="svg-throughput-ops")
    ingest_svg = render_tri_color_bar_svg("Bulk Ingestion Throughput (k rec/s)", ingest_bars, svg_id="svg-throughput-ingest")
    tokens_svg = render_tri_color_bar_svg("LLM Token Footprint (k tokens)", token_bars, svg_id="svg-tokens")
    rss_svg = render_tri_color_bar_svg("Verification Latency & Peak Memory", latency_rss_bars, svg_id="svg-memory-latency")

    if svg_export_dir is not None:
        svg_export_dir.mkdir(parents=True, exist_ok=True)
        (svg_export_dir / "throughput_chart.svg").write_text(ops_svg, encoding="utf-8")
        (svg_export_dir / "ingestion_chart.svg").write_text(ingest_svg, encoding="utf-8")
        (svg_export_dir / "token_savings_chart.svg").write_text(tokens_svg, encoding="utf-8")
        (svg_export_dir / "memory_rss_chart.svg").write_text(rss_svg, encoding="utf-8")

    panels_spec = [
        {
            "slug": "query-throughput",
            "heading": "Query & Cell Throughput",
            "chart_title": "O(1) Field-Map Lookups vs SQLite (M ops/s)",
            "subtitle": "Stacked Bar Layout · Fits Viewport",
            "mode": "canvas",
            "svg_markup": ops_svg,
            "bars": ops_bars,
        },
        {
            "slug": "token-footprint",
            "heading": "LLM Token Savings",
            "chart_title": "BEJSON 105 vs JSON Footprint (k tokens)",
            "subtitle": "SVG Stacked Bar · -68% Reduction",
            "mode": "svg",
            "svg_markup": tokens_svg,
            "bars": token_bars,
        },
        {
            "slug": "bulk-ingestion",
            "heading": "Bulk Ingestion Scale",
            "chart_title": "Bulk Transaction Ingestion (k rec/s)",
            "subtitle": "Canvas Stacked Bar · 15k-60k Rows",
            "mode": "canvas",
            "svg_markup": ingest_svg,
            "bars": ingest_bars,
        },
        {
            "slug": "memory-latency",
            "heading": "Memory & Integrity Gate",
            "chart_title": "Peak RSS (MB) & 15k Verify Gate (ms)",
            "subtitle": "SVG Stacked Bar",
            "mode": "svg",
            "svg_markup": rss_svg,
            "bars": latency_rss_bars,
        },
    ]

    html_content = build_scrollable_dashboard_document("Metrics Showcase", panels_spec)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.write_text(html_content, encoding="utf-8")
    LOGGER_INSTANCE.info("Rendered stacked-bar metrics dashboard to %s", output_html_path)
    return output_html_path


def audit_dashboard_quirks(
    dashboard_html_path: Path,
    screenshots_dir: Path,
) -> Dict[str, Any]:
    """Execute Playwright Chromium DOM, overflow, and ID audit across Desktop (1280x720) and Mobile (390x844)."""
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    chromium_bin = shutil.which("chromium") or shutil.which("chromium-browser") or ""
    if not chromium_bin:
        return {"passed": False, "reason": "chromium binary not found"}

    desktop_png = screenshots_dir / f"{dashboard_html_path.stem}_desktop.png"
    mobile_png = screenshots_dir / f"{dashboard_html_path.stem}_mobile.png"

    audit_script = """
import json, sys
from playwright.sync_api import sync_playwright

url, exec_path, d_out, m_out = sys.argv[1:5]
report = {"desktop": {}, "mobile": {}, "console_errors": [], "duplicate_ids": [], "missing_structural_ids": []}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=exec_path, args=["--no-sandbox", "--disable-gpu"])
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.on("console", lambda m: report["console_errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: report["console_errors"].append(str(e)))
    page.goto(url, wait_until="load")

    dom_audit = page.evaluate('''() => {
        const allWithId = Array.from(document.querySelectorAll("[id]")).map(el => el.id);
        const counts = {};
        allWithId.forEach(id => counts[id] = (counts[id] || 0) + 1);
        const dupes = Object.keys(counts).filter(k => counts[k] > 1);
        const requiredSelectors = ["header", "nav", "main", "footer", "section", ".graph-scroll-viewport", "canvas", "svg"];
        const missing = [];
        requiredSelectors.forEach(sel => {
            document.querySelectorAll(sel).forEach((el, idx) => {
                if (!el.id || !el.id.trim()) missing.push(sel + "[" + idx + "]");
            });
        });
        const viewports = Array.from(document.querySelectorAll(".graph-scroll-viewport")).map(vp => {
            const st = window.getComputedStyle(vp);
            return {
                id: vp.id,
                overflowX: st.overflowX,
                clientWidth: vp.clientWidth,
                scrollWidth: vp.scrollWidth
            };
        });
        return {
            totalIds: allWithId.length,
            dupes,
            missing,
            docScrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            viewports
        };
    }''')
    report["desktop"] = dom_audit
    report["duplicate_ids"] = dom_audit["dupes"]
    report["missing_structural_ids"] = dom_audit["missing"]
    page.screenshot(path=d_out, full_page=True)

    page.set_viewport_size({"width": 390, "height": 844})
    mob_audit = page.evaluate('''() => {
        const viewports = Array.from(document.querySelectorAll(".graph-scroll-viewport")).map(vp => {
            const st = window.getComputedStyle(vp);
            return {
                id: vp.id,
                overflowX: st.overflowX,
                clientWidth: vp.clientWidth,
                scrollWidth: vp.scrollWidth,
                fitsOrScrollsCleanly: st.overflowX === "auto" && vp.clientWidth > 0
            };
        });
        return {
            docScrollWidth: document.documentElement.scrollWidth,
            innerWidth: window.innerWidth,
            pageOverflowQuirk: document.documentElement.scrollWidth > window.innerWidth,
            viewports
        };
    }''')
    report["mobile"] = mob_audit
    page.screenshot(path=m_out, full_page=True)
    browser.close()

print(json.dumps(report))
"""
    proc = subprocess.run(
        [sys.executable, "-c", audit_script, dashboard_html_path.resolve().as_uri(), chromium_bin, str(desktop_png), str(mobile_png)],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if proc.returncode != 0:
        raise MetricsLibraryError(f"Playwright quirk audit failed: {proc.stderr.strip()}", error_code=E_METRICS_RENDER_FAILED)

    audit_data: Dict[str, Any] = json.loads(proc.stdout.strip())
    audit_data["screenshots"] = [str(desktop_png), str(mobile_png)]
    audit_data["passed"] = (
        len(audit_data["console_errors"]) == 0
        and len(audit_data["duplicate_ids"]) == 0
        and len(audit_data["missing_structural_ids"]) == 0
        and not audit_data["mobile"]["pageOverflowQuirk"]
        and all(vp["fitsOrScrollsCleanly"] for vp in audit_data["mobile"]["viewports"])
    )
    return audit_data


def capture_visual_audit_screenshots(
    dashboard_html_path: Path,
    screenshots_dir: Path,
) -> List[Path]:
    """Capture desktop and mobile Playwright screenshots via audit_dashboard_quirks."""
    audit_res = audit_dashboard_quirks(dashboard_html_path, screenshots_dir)
    return [Path(p) for p in audit_res.get("screenshots", []) if Path(p).is_file()]
