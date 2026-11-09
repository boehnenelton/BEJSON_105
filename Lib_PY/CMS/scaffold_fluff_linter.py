#!/usr/bin/env python3
"""
Scaffold Fluff & Zero-Filler Linter
Audits template code files (HTML, BEHTML, JSON) for compliance with Zero Filler Content,
Strictly Functional Placeholders, and Invisible Architecture rules.
"""

import sys
import re
from pathlib import Path

BANNED_FILLER_PATTERNS = [
    r"\blorem\b",
    r"\bipsum\b",
    r"\bdolor\s+sit\b",
    r"\bconsectetur\b",
    r"\bsample\s+text\b",
    r"\bdummy\s+text\b",
    r"\bplaceholder\s+text\b",
    r"\bwelcome\s+to\b",
    r"\bour\s+services\b",
    r"\btestimonials?\b",
]

BANNED_FRAMEWORK_PATTERNS = [
    r"grid\s+space\s+activated",
    r"framework\s+loaded",
    r"lane\s+\d+\s+to\s+\d+\s+active",
    r"container\s+wrapper\s+rendered",
    r"breakpoint\s+triggered",
]

BANNED_IMAGE_HOSTS = [
    r"via\.placeholder\.com",
    r"placeholder\.com",
    r"picsum\.photos",
    r"unsplash\.com",
]


def audit_template(file_path: Path) -> list:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"Unable to read {file_path}: {e}"]

    # 1. Check for lorem ipsum and generic copy filler
    for pattern in BANNED_FILLER_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append(f"Found forbidden filler pattern: '{matches[0]}'")

    # 2. Check for visible framework commentary
    for pattern in BANNED_FRAMEWORK_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append(f"Found visible framework commentary: '{matches[0]}'")

    # 3. Check for fake placeholder image hosts
    for pattern in BANNED_IMAGE_HOSTS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append(f"Found forbidden placeholder image source: '{matches[0]}'")

    # 4. Check for over-length paragraph placeholders (HTML content or BEJSON strings)
    # Strip <style>, <script>, and template about blocks first
    body_content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r"<script[^>]*>.*?</script>", "", body_content, flags=re.DOTALL | re.IGNORECASE)
    body_content = re.sub(r"<section id=[\"']about[\"'][^>]*>.*?</section>", "", body_content, flags=re.DOTALL | re.IGNORECASE)
    html_text_blocks = re.findall(r">([^<]+)<", body_content)
    for block in html_text_blocks:
        clean = block.strip()
        if not clean or clean.startswith("{") or clean.startswith("/*") or clean.startswith("var "):
            continue
        # Check if block looks like an instructional paragraph (> 80 chars)
        if len(clean) > 80 and not clean.startswith("data:"):
            findings.append(f"Overly verbose placeholder text ({len(clean)} chars): '{clean[:40]}...'")

    return findings


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scaffold_fluff_linter.py <template-file-or-dir>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"Path does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    files = [target] if target.is_file() else list(target.glob("**/*.*"))
    target_files = [f for f in files if f.suffix.lower() in (".html", ".htm", ".json", ".bejson", ".txt")]

    total_errors = 0
    print(f"Auditing {len(target_files)} template files under {target.resolve()}...")

    for f in target_files:
        errors = audit_template(f)
        if errors:
            print(f"\nFAIL: {f.name} ({len(errors)} violations):")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)

    if total_errors > 0:
        print(f"\nAudit failed with {total_errors} total filler/framework violations.")
        return 1

    print("\nPASS: All templates conform to Zero Filler Content and Invisible Architecture standards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
