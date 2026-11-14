#!/usr/bin/env python3
"""
Name:           Scaffold_Admin_Entry.py
Family:         CMS
Module Purpose: Lightweight Python/Flask server entry point running on port 5020
                for the Taxonomy-Driven MTV Scaffolding Engine.
Version:        101
Release_Version: 300
Date Created:   2026-11-06
Changelog:      101 (2026-11-12) loopback bind by default, per-process secret key, same-origin POST gate, security headers, output-root config
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  b2cde0bf-d64c-48bb-890d-3f6e9595b695
"""

import os
import sys
import logging
import secrets
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, abort, request

# Dynamically resolve library directories
CURRENT_FILE_DIRECTORY = Path(__file__).resolve().parent
CMS_FAMILY_DIRECTORY = CURRENT_FILE_DIRECTORY.parent
LIB_PY_DIRECTORY = CMS_FAMILY_DIRECTORY.parent
LIBRARIES_105_ROOT_DIRECTORY = LIB_PY_DIRECTORY.parent

for candidate_path in (CMS_FAMILY_DIRECTORY, LIB_PY_DIRECTORY, LIB_PY_DIRECTORY / "Core"):
    if str(candidate_path) not in sys.path:
        sys.path.insert(0, str(candidate_path))

from routes.blueprints import blueprints_bp
from routes.custom_builder import custom_builder_bp
from routes.exporter import exporter_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Scaffold_Admin")

def create_scaffold_admin_application() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(CURRENT_FILE_DIRECTORY / "templates"),
        static_folder=str(CMS_FAMILY_DIRECTORY / "templates")
    )
    # Secret key: from the environment when provided, otherwise a fresh per-process random key.
    app.config["SECRET_KEY"] = os.environ.get("MTV_SCAFFOLD_SECRET_KEY") or secrets.token_hex(32)
    # Every path the API reads or writes is confined to this root (override: MTV_SCAFFOLD_OUTPUT_ROOT).
    output_root = Path(os.environ.get("MTV_SCAFFOLD_OUTPUT_ROOT") or (Path.cwd() / "scaffold_output")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    app.config["MTV_OUTPUT_ROOT"] = str(output_root)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    @app.before_request
    def reject_cross_origin_writes():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and urlparse(origin).netloc != request.host:
                abort(403)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    # Register Administrative Blueprints
    app.register_blueprint(blueprints_bp)
    app.register_blueprint(custom_builder_bp)
    app.register_blueprint(exporter_bp)

    return app

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Taxonomy-Driven MTV Scaffolding Engine Admin Server")
    parser.add_argument("--port", type=int, default=5020, help="Port to bind (default: 5020)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1; the admin API has no authentication, only bind a non-loopback host on a trusted network)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning("Binding %s: this admin API has no authentication.", args.host)
    app = create_scaffold_admin_application()
    logger.info("Starting MTV Scaffolding Dashboard on http://%s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
