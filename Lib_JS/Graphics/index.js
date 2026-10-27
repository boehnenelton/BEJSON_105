/**
 * Index:          Lib_JS/Graphics
 * Family:         Graphics
 * Description:    Main entry point for BEJSON 105a Graphics JavaScript library.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.0
 */

'use strict';

const schemas = require('./lib_bejson_Graphics_graphics_schemas');
const templates = require('./lib_bejson_Graphics_graphics_canvas_templates');

module.exports = {
  ...schemas,
  ...templates
};
