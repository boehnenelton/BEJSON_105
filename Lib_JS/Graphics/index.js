/**
 * Index:          Lib_JS/Graphics
 * Family:         Graphics
 * Description:    Main entry point for BEJSON 105a Graphics JavaScript library.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.1
 * Changelog:      1.0.1 (2026-11-12) header: RELATIONAL_ID recency fingerprint added (code unchanged)
 * RELATIONAL_ID:  3af4899b-cb7b-47ca-8baa-15026cbd208f
 */

'use strict';

const schemas = require('./lib_bejson_Graphics_graphics_schemas');
const templates = require('./lib_bejson_Graphics_graphics_canvas_templates');
const validator = require('./lib_bejson_Graphics_graphics_validator');

module.exports = {
  ...schemas,
  ...templates,
  ...validator
};
