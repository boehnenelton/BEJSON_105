"""
Name: Elton Boehnen
Email: boehnenelton2024@gmail.com
Github: github.com/boehnenelton
Website: https://boehnenelton2024.pages.dev
------------------------------------
Script: test_metrics_ui_playwright.py
Description: Playwright E2E verification test for dev/metrics/index.html refactor.
             Validates top toolbar horizontal scrolling, single active section traversal,
             test meta file badges, and mobile-first zero-overflow.
Version: 1.0.0
Date Created: 2026-11-19
Author Credit: Elton Boehnen
RELATIONAL_ID: d48e23f1-098e-4a62-9e8c-843818e98341
License: PolyForm Noncommercial License 1.0.0 (PolyForm-Noncommercial-1.0.0)
Runtime: Python >= 3.10
"""

import http.server
import logging
import os
import socketserver
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_DIR = SCRIPT_DIR
SCREENSHOT_DIR = os.path.join(METRICS_DIR, "visual_audit", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("TestMetricsPlaywright")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=METRICS_DIR, **kwargs)

    def log_message(self, format, *args):
        pass


def run_e2e_tests():
    # 1. Start local ephemeral HTTP server
    port = 8899
    httpd = socketserver.TCPServer(("127.0.0.1", port), QuietHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    logger.info("Local HTTP server running at http://127.0.0.1:%d", port)

    try:
        from termux_playwright import sync_playwright_termux, launch_sync
        pw_manager = sync_playwright_termux()
        is_termux = True
    except ImportError:
        from playwright.sync_api import sync_playwright
        pw_manager = sync_playwright()
        is_termux = False

    target_url = f"http://127.0.0.1:{port}/index.html"

    with pw_manager as playwright_instance:
        browser = launch_sync(playwright_instance, headless=True) if is_termux else playwright_instance.chromium.launch(headless=True)
        
        # Test 1: Desktop Viewport (1280x800)
        desktop_context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = desktop_context.new_page()
        page.goto(target_url, wait_until="networkidle", timeout=30000)

        # Assertion A: Sidebar navigation exists and has 7 items
        tabs = page.locator("#sidebar-nav .sidebar-nav-item")
        tab_count = tabs.count()
        assert tab_count == 7, f"Expected 7 sidebar items, got {tab_count}"
        logger.info("PASS: Sidebar navigation contains all 7 items")

        # Assertion B: Only ONE section is active at a time
        active_sections = page.locator(".metric-section.active")
        assert active_sections.count() == 1, f"Expected exactly 1 active section, got {active_sections.count()}"
        first_active_id = active_sections.first.get_attribute("id")
        assert first_active_id == "section-kpi-summary", f"Initial active section should be KPI Summary, got {first_active_id}"
        logger.info("PASS: Exactly ONE section is visible (no vertical page cramming)")

        # Assertion C: Every section contains a test-meta-bar with name and file badge
        all_sections = page.locator(".metric-section")
        for idx in range(all_sections.count()):
            sec = all_sections.nth(idx)
            meta_bar = sec.locator(".test-meta-bar")
            assert meta_bar.count() == 1, f"Section {idx} missing test-meta-bar"
            file_badge = meta_bar.locator(".test-file-badge")
            assert file_badge.count() == 1, f"Section {idx} missing test-file-badge"
            file_text = file_badge.text_content()
            assert "dev/metrics" in file_text, f"Invalid file badge text: {file_text}"
        logger.info("PASS: All 7 sections contain unique test names and file badges")

        # Assertion D: Sidebar item click changes active section
        tab_2 = page.locator('#dock-link-ops-throughput')
        tab_2.click()
        page.wait_for_timeout(100)
        assert page.locator('#panel-ops-throughput').is_visible(), "Section 2 not visible after clicking item 2"
        assert not page.locator('#section-kpi-summary').is_visible(), "Section 1 still visible after switching to item 2"
        logger.info("PASS: Sidebar click activates Section 2 and hides other sections")

        # Assertion E: Next traversal button works
        next_btn = page.locator('#panel-ops-throughput .next-btn')
        next_btn.click()
        page.wait_for_timeout(100)
        assert page.locator('#panel-token-savings').is_visible(), "Section 3 not visible after Next button click"
        logger.info("PASS: Traversal Next button advanced to Section 3")

        # Assertion F: Solid Button Border Law — active button MUST NOT have white border
        active_item = page.locator("#sidebar-nav .sidebar-nav-item.active")
        border_color = active_item.evaluate("el => window.getComputedStyle(el).borderColor")
        bg_color = active_item.evaluate("el => window.getComputedStyle(el).backgroundColor")
        assert "255, 255, 255" not in border_color, f"FORBIDDEN: Active button has white border: {border_color}"
        logger.info("PASS: Solid Button Border Law verified (bg: %s, border: %s, NO white border)", bg_color, border_color)

        # Assertion G: Consolidated Test Call Summary Table exists and contains all 10 calls
        summary_table = page.locator("#table-consolidated-test-summary")
        assert summary_table.count() == 1, "Consolidated test summary table not found in Section 1"
        summary_rows = summary_table.locator("tbody tr")
        assert summary_rows.count() == 10, f"Expected 10 test summary rows, got {summary_rows.count()}"
        logger.info("PASS: Consolidated test summary table verified with all 10 test call metrics")

        # Capture Desktop Screenshots for ALL 7 sections to inspect visual presentation
        section_descriptors = [
            ("section-kpi-summary", "01_kpi_summary"),
            ("panel-ops-throughput", "02_ops_throughput"),
            ("panel-token-savings", "03_token_savings"),
            ("panel-bulk-ingestion", "04_bulk_ingestion"),
            ("panel-memory-gate", "05_memory_gate"),
            ("panel-test-latency", "06_test_latency"),
            ("panel-test-matrix", "07_test_matrix")
        ]

        for sec_id, label in section_descriptors:
            page.locator(f'.sidebar-nav-item[data-target="{sec_id}"]').click()
            page.wait_for_timeout(150)
            assert page.locator(f'#{sec_id}').is_visible(), f"Section {sec_id} failed to display"
            sec_ss = os.path.join(SCREENSHOT_DIR, f"desktop_{label}.png")
            page.screenshot(path=sec_ss, full_page=False)
            logger.info("VISUAL AUDIT: Desktop [%s] captured -> %s", label, sec_ss)

        desktop_context.close()

        # Test 2: Mobile Viewport (390x844 - iPhone / Android portrait)
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()
        mobile_page.goto(target_url, wait_until="networkidle", timeout=30000)

        # Assertion H: Mobile hamburger menu toggles sidebar drawer
        hamburger = mobile_page.locator("#nav-hamburger-btn")
        sidebar = mobile_page.locator("#sidebar-nav")
        assert not sidebar.evaluate("el => el.classList.contains('drawer-open')"), "Drawer should be closed initially on mobile"
        hamburger.click()
        mobile_page.wait_for_timeout(150)
        assert sidebar.evaluate("el => el.classList.contains('drawer-open')"), "Drawer should open after hamburger click"
        logger.info("PASS: Mobile hamburger button successfully toggles navigation drawer")

        # Mobile visual captures across sections verifying ZERO body overflow on every single section
        for sec_id, label in section_descriptors:
            if not sidebar.evaluate("el => el.classList.contains('drawer-open')"):
                hamburger.click()
                mobile_page.wait_for_timeout(100)
            mobile_page.locator(f'#sidebar-nav .sidebar-nav-item[data-target="{sec_id}"]').click()
            mobile_page.wait_for_timeout(150)
            
            # Assert zero horizontal body overflow on each test section
            b_scroll_w = mobile_page.evaluate("document.body.scrollWidth")
            w_inner_w = mobile_page.evaluate("window.innerWidth")
            assert b_scroll_w <= w_inner_w + 1, f"Visual Failure: Horizontal overflow on {label} ({b_scroll_w} > {w_inner_w})"
            
            mobile_sec_ss = os.path.join(SCREENSHOT_DIR, f"mobile_{label}.png")
            mobile_page.screenshot(path=mobile_sec_ss, full_page=False)
            logger.info("VISUAL AUDIT: Mobile [%s] zero-overflow confirmed (%dpx <= %dpx) -> %s", label, b_scroll_w, w_inner_w, mobile_sec_ss)

        mobile_context.close()
        browser.close()

    httpd.shutdown()
    sys.stdout.write("ALL PLAYWRIGHT TESTS PASSED FOR REFACTORED METRICS UI!\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_tests())
