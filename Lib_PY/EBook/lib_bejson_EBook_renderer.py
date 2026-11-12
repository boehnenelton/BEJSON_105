"""
Library:         lib_bejson_EBook_renderer.py
Family:          EBook
Module Purpose:  Modern semantic HTML5 and BECSS Tri-Color layout renderer for EBook library family (strictly no html3).
Architecture:    BEJSON 104 Presentation Layer enforcing WCAG AAA Tri-Color contrast, responsive typography, and subpage routing.
Version:         1.0.0
Release_Version: 300
Date:            2026-11-11
Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Format_Creator:  Elton Boehnen
RELATIONAL_ID:   480a0004-e000-11ef-9000-000000000004
License:         PolyForm-Noncommercial-1.0.0
"""

from datetime import datetime, timezone
import html as html_escape_module
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

try:
    from .lib_bejson_EBook_core import (
        EBookEntityRecord,
        format_inline_markdown,
    )
except ImportError:
    from lib_bejson_EBook_core import (
        EBookEntityRecord,
        format_inline_markdown,
    )

AUTHOR_CREDIT: str = "Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton"


def get_shared_becss_tokens() -> str:
    """Return authoritative BECSS Tri-Color responsive CSS tokens (semantic HTML5, zero html3)."""
    return """
    :root {
      --accent-red: #DE2626;
      --accent-red-hover: #EF4444;
      --accent-blue: #3B82F6;
      --accent-green: #10B981;
      --radius-sm: 4px;
      --radius-main: 8px;
      --font-body: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-heading: 'Playfair Display', Georgia, serif;
      --font-mono: 'Source Code Pro', "JetBrains Mono", Menlo, Consolas, monospace;
    }

    [data-theme="dark"] {
      --bg-base: #000000;
      --bg-surface: #0a0a0a;
      --bg-elevated: #141414;
      --border-color: #262626;
      --border-subtle: #1a1a1a;
      --fg-primary: #FFFFFF;
      --fg-secondary: #A3A3A3;
      --fg-muted: #737373;
      --chip-bg: #171717;
      --card-hover-border: #DE2626;
      --code-bg: #0d0d0d;
      --quote-bg: #121212;
      --shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.5);
    }

    [data-theme="light"] {
      --bg-base: #FFFFFF;
      --bg-surface: #F9FAFB;
      --bg-elevated: #F3F4F6;
      --border-color: #E5E7EB;
      --border-subtle: #F3F4F6;
      --fg-primary: #111827;
      --fg-secondary: #4B5563;
      --fg-muted: #9CA3AF;
      --chip-bg: #F3F4F6;
      --card-hover-border: #DE2626;
      --code-bg: #F3F4F6;
      --quote-bg: #F9FAFB;
      --shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.06);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-base);
      color: var(--fg-primary);
      font-family: var(--font-body);
      line-height: 1.65;
      -webkit-font-smoothing: antialiased;
      padding: 24px 16px 80px 16px;
      transition: background-color 0.2s ease, color 0.2s ease;
    }

    .becss-portal-shell {
      max-width: 1040px;
      margin: 0 auto;
    }

    /* Top Breadcrumb Navigation */
    .becss-breadcrumbs {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--fg-secondary);
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .becss-crumb-link {
      color: var(--fg-secondary);
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .becss-crumb-link:hover {
      color: var(--accent-red);
    }

    .becss-crumb-sep {
      color: var(--fg-muted);
    }

    .becss-crumb-active {
      color: var(--fg-primary);
      font-weight: 600;
    }

    /* Header Bar */
    .becss-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-main);
      margin-bottom: 24px;
    }

    .becss-brand-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .becss-cube-icon {
      width: 18px;
      height: 18px;
      background: var(--accent-red);
      display: inline-block;
      clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
    }

    .becss-brand-title {
      font-family: var(--font-heading);
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--fg-primary);
      text-decoration: none;
    }

    .becss-brand-title:hover {
      color: var(--accent-red);
    }

    .becss-theme-toggle {
      background: var(--chip-bg);
      border: 1px solid var(--border-color);
      color: var(--fg-primary);
      font-family: var(--font-mono);
      font-size: 12px;
      padding: 6px 14px;
      border-radius: 999px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .becss-theme-toggle:hover {
      border-color: var(--accent-red);
      color: var(--accent-red);
    }

    /* Reading Telemetry Banner (Horizontal Scrolling Dock Strip) */
    .becss-telemetry-banner {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      gap: 10px;
      margin-bottom: 20px;
      padding-bottom: 6px;
      scrollbar-width: thin;
    }

    .telemetry-card {
      flex: 0 0 auto;
      min-width: 140px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 10px 14px;
      text-align: left;
    }

    .telemetry-label {
      font-family: var(--font-mono);
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--fg-muted);
      margin-bottom: 2px;
      white-space: nowrap;
    }

    .telemetry-val {
      font-size: 1.15rem;
      font-weight: 700;
      font-family: var(--font-heading);
      color: var(--fg-primary);
      white-space: nowrap;
      line-height: 1.2;
    }

    /* Search & Filter Input */
    .becss-search-wrap {
      margin-bottom: 28px;
    }

    .becss-search-input {
      width: 100%;
      padding: 12px 18px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--fg-primary);
      font-family: var(--font-body);
      font-size: 14px;
      outline: none;
      transition: border-color 0.15s ease;
    }

    .becss-search-input:focus {
      border-color: var(--accent-red);
    }

    /* Navigation Card Grid (Master Hub) */
    .hub-card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
      margin-bottom: 48px;
    }

    @media (max-width: 640px) {
      .hub-card-grid {
        grid-template-columns: 1fr;
      }
    }

    .hub-nav-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-main);
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s ease, border-color 0.15s ease;
      position: relative;
    }

    .hub-nav-card:hover {
      border-color: var(--card-hover-border);
      transform: translateY(-2px);
    }

    .hub-card-badge {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-red);
      font-weight: 600;
      margin-bottom: 8px;
      text-transform: uppercase;
    }

    .hub-card-title {
      font-family: var(--font-heading);
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 12px;
      line-height: 1.35;
    }

    .hub-card-title a {
      color: var(--fg-primary);
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .hub-card-title a:hover {
      color: var(--accent-red);
    }

    .hub-card-excerpt {
      font-size: 13.5px;
      color: var(--fg-secondary);
      line-height: 1.55;
      margin-bottom: 16px;
      flex-grow: 1;
    }

    .hub-card-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 18px;
    }

    .meta-chip {
      background: var(--chip-bg);
      border: 1px solid var(--border-color);
      border-radius: 999px;
      padding: 3px 10px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--fg-secondary);
    }

    .chip-speaker {
      color: var(--accent-blue);
      border-color: rgba(59, 130, 246, 0.3);
    }

    .becss-card-btn {
      display: inline-block;
      text-align: center;
      background: var(--accent-red);
      color: #FFFFFF !important;
      text-decoration: none;
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: var(--radius-sm);
      transition: background-color 0.15s ease;
    }

    .becss-card-btn:hover {
      background: var(--accent-red-hover);
    }

    /* Subpage Specific Layouts */
    .becss-subpage-action-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 10px;
    }

    .becss-nav-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      background: var(--chip-bg);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      color: var(--fg-primary);
      text-decoration: none;
      font-size: 13px;
      font-family: var(--font-mono);
      transition: all 0.15s ease;
    }

    .becss-nav-btn:hover:not(.disabled) {
      border-color: var(--accent-red);
      color: var(--accent-red);
    }

    .becss-nav-btn.disabled {
      opacity: 0.4;
      pointer-events: none;
    }

    .becss-tracker-pill {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--fg-muted);
    }

    .becss-chapter-paging-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin: 20px 0;
      flex-wrap: wrap;
    }

    /* Cover Hero Card */
    .becss-cover-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-main);
      padding: 36px 32px;
      margin-bottom: 32px;
    }

    .becss-badge-eyebrow {
      font-family: var(--font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent-red);
      font-weight: 600;
      margin-bottom: 12px;
    }

    .becss-cover-title {
      font-family: var(--font-heading);
      font-size: 2.2rem;
      font-weight: 700;
      margin-bottom: 12px;
      line-height: 1.25;
    }

    .becss-cover-sub {
      font-size: 1rem;
      color: var(--fg-secondary);
      margin-bottom: 20px;
    }

    /* Table of Contents */
    .becss-toc-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-main);
      padding: 28px;
      margin-bottom: 36px;
    }

    .becss-toc-title {
      font-family: var(--font-heading);
      font-size: 1.35rem;
      font-weight: 700;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }

    .becss-toc-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .becss-toc-item {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      font-size: 14px;
    }

    .becss-toc-link {
      color: var(--fg-primary);
      text-decoration: none;
      transition: color 0.15s ease;
    }

    .becss-toc-link:hover {
      color: var(--accent-red);
    }

    .becss-toc-leader {
      flex: 1;
      border-bottom: 1px dotted var(--border-color);
      margin: 0 12px;
    }

    .becss-toc-page {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--fg-muted);
    }

    /* Document Sections & Semantic Blocks */
    .becss-section-article {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-main);
      padding: 32px 28px;
      margin-bottom: 32px;
      page-break-after: always;
    }

    .section-header {
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 14px;
      margin-bottom: 22px;
    }

    .section-eyebrow {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--accent-red);
      font-weight: 600;
      text-transform: uppercase;
    }

    .section-title {
      font-family: var(--font-heading);
      font-size: 1.6rem;
      font-weight: 700;
      margin-top: 4px;
    }

    .section-timestamp {
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--fg-muted);
      margin-top: 2px;
    }

    .becss-paragraph {
      margin-bottom: 16px;
      font-size: 15px;
      line-height: 1.7;
      color: var(--fg-primary);
    }

    .becss-blockquote {
      background: var(--quote-bg);
      border-left: 3px solid var(--accent-red);
      padding: 14px 18px;
      margin-bottom: 18px;
      font-style: italic;
      color: var(--fg-secondary);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    }

    .becss-code-block {
      background: var(--code-bg);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 16px;
      margin-bottom: 18px;
      overflow-x: auto;
      font-family: var(--font-mono);
      font-size: 13px;
      line-height: 1.5;
    }

    .becss-list-item {
      margin-left: 24px;
      margin-bottom: 8px;
      font-size: 15px;
    }

    /* Dialogue Turn Card (if audio/speech transcript format) */
    .becss-turn-card {
      border-left: 3px solid var(--border-color);
      padding: 12px 16px;
      margin-bottom: 14px;
      background: var(--chip-bg);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    }

    .turn-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
      font-family: var(--font-mono);
      font-size: 12px;
    }

    .turn-speaker-badge {
      font-weight: 600;
      color: var(--accent-blue);
    }

    .turn-timestamp {
      color: var(--fg-muted);
    }

    .turn-body {
      font-size: 14.5px;
      line-height: 1.6;
    }

    .speaker-accent-a { border-left-color: #3B82F6; }
    .speaker-accent-b { border-left-color: #10B981; }
    .speaker-accent-c { border-left-color: #F59E0B; }

    /* Footer */
    .becss-portal-footer {
      text-align: center;
      margin-top: 60px;
      padding-top: 24px;
      border-top: 1px solid var(--border-color);
      font-size: 12px;
      color: var(--fg-muted);
      font-family: var(--font-mono);
    }

    /* Print Styles */
    @media print {
      body {
        background: #FFFFFF !important;
        color: #000000 !important;
        padding: 0 !important;
      }
      .becss-theme-toggle, .becss-search-wrap, .becss-breadcrumbs, .becss-subpage-action-bar, .becss-chapter-paging-bar {
        display: none !important;
      }
      .becss-section-article {
        border: none !important;
        background: transparent !important;
        page-break-after: always;
      }
    }
    """


def render_master_hub_html(
    manifest_records: List[EBookEntityRecord],
    portal_title: str = "Publications & E-Book Portal",
    portal_subtitle: str = "Semantic Multi-Page Navigation Hub & Subpage Directory",
    theme: str = "dark",
    taxonomy_name: str = "transcripts",
) -> str:
    """
    Renders the Master Navigation Hub (index.html).
    Strictly complies with the Multi-Page Web Architecture & Subpage Routing Invariant:
      - Master index serves exclusively as a navigation directory
      - Displays telemetry counters, search filter, and 2-column card grid
      - Merging or concatenating full entity bodies inline on index is STRICTLY PROHIBITED.
    """
    total_records = len(manifest_records)
    total_words = sum(r.word_count for r in manifest_records)
    total_minutes = sum(r.reading_time_minutes for r in manifest_records)
    total_sections = sum(r.sections_count for r in manifest_records)
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cards_html: List[str] = []
    for idx, rec in enumerate(manifest_records, 1):
        safe_title = html_escape_module.escape(rec.title)
        safe_excerpt = html_escape_module.escape(rec.excerpt)
        subpage_url = html_escape_module.escape(rec.subpage_rel_path)

        search_tokens = html_escape_module.escape(f"{rec.title} {rec.slug} {rec.excerpt}".lower())

        cards_html.append(f"""
        <article class="hub-nav-card" data-search="{search_tokens}">
          <div>
            <div class="hub-card-badge">Document #{idx:02d} · {html_escape_module.escape(rec.taxonomy.upper())}</div>
            <h2 class="hub-card-title"><a href="{subpage_url}">{safe_title}</a></h2>
            <div class="hub-card-meta">
              <span class="meta-chip">📖 {rec.word_count:,} words</span>
              <span class="meta-chip">⏱️ ~{rec.reading_time_minutes} min read</span>
              <span class="meta-chip">📑 {rec.sections_count} sections</span>
            </div>
            <p class="hub-card-excerpt">{safe_excerpt}</p>
          </div>
          <div style="margin-top: 14px;">
            <a href="{subpage_url}" class="becss-card-btn">Open Subpage &rarr;</a>
          </div>
        </article>
        """)

    theme_attr = "dark" if theme.lower() == "dark" else "light"

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme_attr}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_escape_module.escape(portal_title)}</title>
  <meta name="description" content="{html_escape_module.escape(portal_subtitle)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
  <style>
{get_shared_becss_tokens()}
  </style>
</head>
<body>
  <div class="becss-portal-shell">
    <header class="becss-header-row">
      <div class="becss-brand-wrap">
        <span class="becss-cube-icon" aria-hidden="true"></span>
        <a href="index.html" class="becss-brand-title">{html_escape_module.escape(portal_title)}</a>
      </div>
      <button class="becss-theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark/light theme">🌓 Theme</button>
    </header>

    <section class="becss-telemetry-banner" aria-label="Portal Metrics">
      <div class="telemetry-card">
        <div class="telemetry-label">Total Documents</div>
        <div class="telemetry-val">{total_records}</div>
      </div>
      <div class="telemetry-card">
        <div class="telemetry-label">Reading Time</div>
        <div class="telemetry-val">~{total_minutes} min</div>
      </div>
      <div class="telemetry-card">
        <div class="telemetry-label">Total Words</div>
        <div class="telemetry-val">{total_words:,}</div>
      </div>
      <div class="telemetry-card">
        <div class="telemetry-label">Semantic Sections</div>
        <div class="telemetry-val">{total_sections}</div>
      </div>
    </section>

    <section class="becss-search-wrap">
      <input type="text" id="searchInput" class="becss-search-input" placeholder="Instant filter documents by title, keyword, or slug..." onkeyup="filterHubCards()" aria-label="Filter documents">
    </section>

    <main class="hub-card-grid" id="hubGrid">
      {"".join(cards_html)}
    </main>

    <footer class="becss-portal-footer">
      <p>{AUTHOR_CREDIT}</p>
      <p>Compiled by lib_bejson_ebook · PolyForm Noncommercial 1.0.0 · {today_date}</p>
    </footer>
  </div>

  <script>
    function toggleTheme() {{
      const htmlEl = document.documentElement;
      const current = htmlEl.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      htmlEl.setAttribute('data-theme', nextTheme);
      localStorage.setItem('bejson_ebook_theme', nextTheme);
    }}

    function filterHubCards() {{
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const cards = document.querySelectorAll('.hub-nav-card');
      cards.forEach(card => {{
        const searchData = card.getAttribute('data-search') || '';
        card.style.display = searchData.includes(query) ? '' : 'none';
      }});
    }}

    (function() {{
      const saved = localStorage.getItem('bejson_ebook_theme');
      if (saved) {{
        document.documentElement.setAttribute('data-theme', saved);
      }}
    }})();
  </script>
</body>
</html>
"""


def render_subpage_html(
    parsed_doc: Dict[str, Any],
    slug: str,
    current_index: int,
    total_count: int,
    taxonomy: str = "transcripts",
    prev_record: Optional[EBookEntityRecord] = None,
    next_record: Optional[EBookEntityRecord] = None,
    relative_hub_path: str = "../../index.html",
    relative_taxonomy_path: str = "../index.html",
    theme: str = "dark",
) -> str:
    """
    Renders an individual modular subpage (<domain>/<taxonomy>/pages/<slug>/index.html).
    Complies with the Subpage Invariant:
      - Backward breadcrumb rail to Hub & Taxonomy
      - Prev / Next chapter chaining
      - Full semantic document content with zero truncation
      - Table of Contents with dotted leader lines
    """
    title = html_escape_module.escape(parsed_doc.get("title", "Untitled Document"))
    word_count = parsed_doc.get("word_count", 0)
    reading_time = parsed_doc.get("reading_time_minutes", 1)
    sections = parsed_doc.get("sections", [])
    speakers = parsed_doc.get("speakers", [])
    today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Table of Contents
    toc_items: List[str] = []
    for idx, sec in enumerate(sections, 1):
        sec_title = html_escape_module.escape(sec.get("title", f"Section {idx}"))
        anchor = html_escape_module.escape(sec.get("anchor", f"sec-{idx}"))
        start_ts = html_escape_module.escape(sec.get("start_time", ""))
        ts_label = start_ts if start_ts else f"§ {idx}"

        toc_items.append(f"""
        <li class="becss-toc-item">
          <a href="#{anchor}" class="becss-toc-link">{sec_title}</a>
          <span class="becss-toc-leader"></span>
          <span class="becss-toc-page">{ts_label}</span>
        </li>
        """)

    # Render Sections and Blocks
    sections_html: List[str] = []
    for idx, sec in enumerate(sections, 1):
        sec_title = html_escape_module.escape(sec.get("title", f"Section {idx}"))
        anchor = html_escape_module.escape(sec.get("anchor", f"sec-{idx}"))
        start_ts = sec.get("start_time", "")
        ts_html = f'<div class="section-timestamp">Starts at {html_escape_module.escape(start_ts)}</div>' if start_ts else ""

        blocks_html: List[str] = []
        for blk in sec.get("blocks", []):
            btype = blk.get("type", "paragraph")

            if btype == "paragraph":
                blocks_html.append(f'<p class="becss-paragraph">{format_inline_markdown(blk.get("text", ""))}</p>')
            elif btype == "blockquote":
                blocks_html.append(f'<blockquote class="becss-blockquote">{format_inline_markdown(blk.get("text", ""))}</blockquote>')
            elif btype == "code":
                blocks_html.append(f'<pre class="becss-code-block"><code>{html_escape_module.escape(blk.get("content", ""))}</code></pre>')
            elif btype == "list_item":
                blocks_html.append(f'<li class="becss-list-item">{format_inline_markdown(blk.get("text", ""))}</li>')
            elif btype == "heading3":
                blocks_html.append(f'<h3 style="margin: 20px 0 10px 0; font-family: var(--font-heading); font-size: 1.25rem;">{html_escape_module.escape(blk.get("title", ""))}</h3>')
            elif btype == "dialogue_turn":
                spk = html_escape_module.escape(blk.get("speaker", "Speaker"))
                ts = html_escape_module.escape(blk.get("timestamp", ""))
                txt = format_inline_markdown(blk.get("text", ""))

                clean_spk = spk.lower().strip()
                accent_class = "speaker-accent-default"
                if clean_spk.endswith(" a"):
                    accent_class = "speaker-accent-a"
                elif clean_spk.endswith(" b"):
                    accent_class = "speaker-accent-b"
                elif clean_spk.endswith(" c"):
                    accent_class = "speaker-accent-c"

                blocks_html.append(f"""
                <article class="becss-turn-card {accent_class}">
                  <div class="turn-header">
                    <span class="turn-speaker-badge">{spk}</span>
                    <span class="turn-timestamp">{ts}</span>
                  </div>
                  <div class="turn-body">{txt}</div>
                </article>
                """)

        sections_html.append(f"""
        <article class="becss-section-article" id="{anchor}">
          <header class="section-header">
            <div class="section-eyebrow">Section {idx:02d}</div>
            <h2 class="section-title">{sec_title}</h2>
            {ts_html}
          </header>
          <div class="section-body">
            {"".join(blocks_html)}
          </div>
        </article>
        """)

    # Navigation buttons
    prev_btn_html = (
        f'<a href="../{prev_record.slug}/index.html" class="becss-nav-btn">&larr; {html_escape_module.escape(prev_record.title)}</a>'
        if prev_record else '<span class="becss-nav-btn disabled">&larr; First Document</span>'
    )
    next_btn_html = (
        f'<a href="../{next_record.slug}/index.html" class="becss-nav-btn">{html_escape_module.escape(next_record.title)} &rarr;</a>'
        if next_record else '<span class="becss-nav-btn disabled">Last Document &rarr;</span>'
    )

    speaker_chips = "".join(
        f'<span class="meta-chip chip-speaker">🎙️ {html_escape_module.escape(s)}</span>'
        for s in speakers
    )

    theme_attr = "dark" if theme.lower() == "dark" else "light"

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme_attr}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · E-Book</title>
  <meta name="description" content="Dedicated e-book subpage: {title}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
  <style>
{get_shared_becss_tokens()}
  </style>
</head>
<body>
  <div class="becss-portal-shell">
    <nav class="becss-breadcrumbs" aria-label="Breadcrumb Trail">
      <a href="{relative_hub_path}" class="becss-crumb-link">E-Book Hub</a>
      <span class="becss-crumb-sep">/</span>
      <a href="{relative_taxonomy_path}" class="becss-crumb-link">{html_escape_module.escape(taxonomy.title())}</a>
      <span class="becss-crumb-sep">/</span>
      <span class="becss-crumb-active">{title}</span>
    </nav>

    <div class="becss-subpage-action-bar">
      <a href="{relative_hub_path}" class="becss-nav-btn">&larr; Back to Hub</a>
      <span class="becss-tracker-pill">Document {current_index} of {total_count}</span>
      <button class="becss-theme-toggle" onclick="toggleTheme()" aria-label="Toggle dark/light theme">🌓 Theme</button>
    </div>

    <div class="becss-chapter-paging-bar">
      {prev_btn_html}
      {next_btn_html}
    </div>

    <header class="becss-cover-card">
      <div class="becss-badge-eyebrow">lib_bejson_ebook · Subpage Edition</div>
      <h1 class="becss-cover-title">{title}</h1>
      <p class="becss-cover-sub">Structured Semantic Publication Record</p>
      <div class="hub-card-meta">
        <span class="meta-chip">📖 {word_count:,} words</span>
        <span class="meta-chip">⏱️ ~{reading_time} min read</span>
        <span class="meta-chip">📑 {len(sections)} sections</span>
        <span class="meta-chip">📅 {today_date}</span>
        {speaker_chips}
      </div>
    </header>

    <section class="becss-toc-card">
      <h2 class="becss-toc-title">Table of Contents</h2>
      <ul class="becss-toc-list">
        {"".join(toc_items)}
      </ul>
    </section>

    <main>
      {"".join(sections_html)}
    </main>

    <div class="becss-chapter-paging-bar">
      {prev_btn_html}
      <a href="{relative_hub_path}" class="becss-nav-btn">Hub</a>
      {next_btn_html}
    </div>

    <footer class="becss-portal-footer">
      <p>{AUTHOR_CREDIT}</p>
      <p>Compiled by lib_bejson_ebook · PolyForm Noncommercial 1.0.0 · {today_date}</p>
    </footer>
  </div>

  <script>
    function toggleTheme() {{
      const htmlEl = document.documentElement;
      const current = htmlEl.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      htmlEl.setAttribute('data-theme', nextTheme);
      localStorage.setItem('bejson_ebook_theme', nextTheme);
    }}

    (function() {{
      const saved = localStorage.getItem('bejson_ebook_theme');
      if (saved) {{
        document.documentElement.setAttribute('data-theme', saved);
      }}
    }})();
  </script>
</body>
</html>
"""
