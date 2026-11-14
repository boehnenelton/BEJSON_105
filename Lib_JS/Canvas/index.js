/**
 * Index:          Lib_JS/Canvas
 * Family:         Canvas
 * Description:    Entry point re-exporting the Canvas schemas and templates modules.
 * Version:        1.0.0
 * RELATIONAL_ID:  b853967f-d0ec-4912-bc3e-fe9c2b9d89e9
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 */
'use strict';
module.exports = {
  ...require('./lib_bejson_Canvas_canvas_schemas.js'),
  ...require('./lib_bejson_Canvas_canvas_templates.js')
};
