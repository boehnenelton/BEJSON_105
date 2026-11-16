/**
 * Unit tests for libraries_105 Lib_JS/Gaming_Editors family.
 */

'use strict';

const assert = require('assert');
const {
  E_GAMING_EDITORS_CORE_VALIDATION_FAILED,
  ERROR_NAMES,
  GamingEditorsValidationError,
  GAMING_SPRITE_STUDIO_FIELDS,
  createSpriteStudioConfig105a,
  buildFieldMap105,
  listGamingEditorTemplates
} = require('../index.js');

// 1. Error codes range test
assert.strictEqual(E_GAMING_EDITORS_CORE_VALIDATION_FAILED, 520);
assert.strictEqual(ERROR_NAMES[520], 'E_GAMING_EDITORS_CORE_VALIDATION_FAILED');
const err = new GamingEditorsValidationError('Test error', 520);
assert.strictEqual(err.code, 520);
assert(err.message.includes('E_GAMING_EDITORS_CORE_VALIDATION_FAILED'));

// 2. Schema generation test
const doc = createSpriteStudioConfig105a({
  editor_id: 'js_sprite_studio',
  canvas_size_px: 512,
  cell_size_px: 32
});
assert.strictEqual(doc.Format, 'BEJSON');
assert.strictEqual(doc.Format_Version, '105a');
assert.strictEqual(doc.Records_Type[0], 'GamingSpriteStudioConfig');

// 3. Field map caching test
const fmap = buildFieldMap105(doc);
assert.strictEqual(fmap.record_uuid, 0);
assert.strictEqual(fmap.editor_id, 1);

// 4. Template catalog test
const tpls = listGamingEditorTemplates();
assert.strictEqual(tpls.length, 4);

console.log('All Lib_JS/Gaming_Editors tests passed successfully.');
