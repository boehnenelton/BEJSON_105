#!/usr/bin/env python3
"""
Name:           Scaffold_Admin_Entry.py
Family:         CMS
Module Purpose: Lightweight Python/Flask server entry point running on port 5020
                for the Taxonomy-Driven MTV Scaffolding Engine.
Version:        100
Release_Version: 300
Date Created:   2026-11-06
Author Credit:  Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
RELATIONAL_ID:  7e29a410-9831-4bcf-8f52-51c07e8912d3
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask

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
    app.config["SECRET_KEY"] = "mtv-scaffold-secret-key-105"

    # Register Administrative Blueprints
    app.register_blueprint(blueprints_bp)
    app.register_blueprint(custom_builder_bp)
    app.register_blueprint(exporter_bp)

    return app

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Taxonomy-Driven MTV Scaffolding Engine Admin Server")
    parser.add_argument("--port", type=int, default=5020, help="Port to bind (default: 5020)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    app = create_scaffold_admin_application()
    logger.info("Starting MTV Scaffolding Dashboard on http://%s:%d", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
