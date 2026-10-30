/**
 * Library:        lib_bejson_Canvas_canvas_schemas.js
 * Family:         Canvas
 * Description:    BEJSON 105a Schema Definitions and Validation for SVG Canvas Templates,
 *                 Animation Framerates, Dimensions, and Playwright Capture Pipelines.
 * BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * MFDB:           MFDB stands for Multi File Database. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * Version:        1.0.0
 * Date:           2026-10-25
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * RELATIONAL_ID:  5f9a1c2e-3d4b-4a5c-8901-2e3f4a5b6c7d
 * Release_Version: 300
 */

'use strict';

const CANVAS_STUDIO_CONFIG_FIELDS = [
  { name: 'canvas_id',         type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000001' },
  { name: 'template_name',     type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000002' },
  { name: 'stage_selector',    type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000003' },
  { name: 'width_px',          type: 'integer', field_uuid: '7a1b2c3d-1111-4000-8000-000000000004' },
  { name: 'height_px',         type: 'integer', field_uuid: '7a1b2c3d-1111-4000-8000-000000000005' },
  { name: 'aspect_ratio',      type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000006' },
  { name: 'bg_theme',          type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000007' },
  { name: 'accent_color',      type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000008' },
  { name: 'animation_name',    type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000009' },
  { name: 'duration_sec',      type: 'number',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000010' },
  { name: 'fps',               type: 'integer', field_uuid: '7a1b2c3d-1111-4000-8000-000000000011' },
  { name: 'total_frames',      type: 'integer', field_uuid: '7a1b2c3d-1111-4000-8000-000000000012' },
  { name: 'device_scale',      type: 'integer', field_uuid: '7a1b2c3d-1111-4000-8000-000000000013' },
  { name: 'export_format',     type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000014' },
  { name: 'output_path',       type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000015' },
  { name: 'svg_source_mode',   type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000016' },
  { name: 'svg_inline_markup', type: 'string',  field_uuid: '7a1b2c3d-1111-4000-8000-000000000017' }
];

const CANVAS_FRAME_SEQUENCE_FIELDS = [
  { name: 'frame_index',      type: 'integer', field_uuid: '8b2c3d4e-2222-4000-8000-000000000001' },
  { name: 'seek_progress',    type: 'number',  field_uuid: '8b2c3d4e-2222-4000-8000-000000000002' },
  { name: 'timestamp_sec',    type: 'number',  field_uuid: '8b2c3d4e-2222-4000-8000-000000000003' },
  { name: 'frame_filename',   type: 'string',  field_uuid: '8b2c3d4e-2222-4000-8000-000000000004' },
  { name: 'is_rendered_flag', type: 'boolean', field_uuid: '8b2c3d4e-2222-4000-8000-000000000005' },
  { name: 'checksum_sha256',  type: 'string',  field_uuid: '8b2c3d4e-2222-4000-8000-000000000006' }
];

function generateUuidV4() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function buildFieldMap105(fields) {
  const fieldMap = {};
  for (let i = 0; i < fields.length; i++) {
    // 105a row offset: row[0] is record_uuid, so fields start at index 1
    fieldMap[fields[i].name] = i + 1;
  }
  return fieldMap;
}

function createCanvasConfig105a(options = {}) {
  const durationSec = options.duration_sec ?? 8.0;
  const fps = options.fps ?? 60;
  const totalFrames = options.total_frames ?? Math.max(1, Math.ceil(durationSec * fps));

  const valuesRow = [
    options.record_uuid || generateUuidV4(),
    options.canvas_id || 'canvas_stage_01',
    options.template_name || 'template_square_800x800.html',
    options.stage_selector || '#capture-stage',
    parseInt(options.width_px ?? 800, 10),
    parseInt(options.height_px ?? 800, 10),
    options.aspect_ratio || '1:1',
    options.bg_theme || '#000000',
    options.accent_color || '#DE2626',
    options.animation_name || 'pulseCore',
    parseFloat(durationSec),
    parseInt(fps, 10),
    parseInt(totalFrames, 10),
    parseInt(options.device_scale ?? 2, 10),
    options.export_format || 'png',
    options.output_path || 'captures/stage_frame.png',
    options.svg_source_mode || 'template_default',
    options.svg_inline_markup || ''
  ];

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Records_Type: ['CanvasStudioConfig'],
    Fields: CANVAS_STUDIO_CONFIG_FIELDS.map(f => ({ ...f })),
    Values: [valuesRow]
  };
}

function createFrameSequence105a(durationSec, fps, totalFrames = null, outputDir = 'captures/frames', prefix = 'frame_') {
  if (!totalFrames || totalFrames <= 0) {
    totalFrames = Math.max(1, Math.ceil(durationSec * fps));
  }
  const timeStepSec = totalFrames > 1 ? durationSec / (totalFrames - 1) : 0.0;
  const valuesRows = [];

  for (let i = 0; i < totalFrames; i++) {
    const progress = totalFrames > 1 ? i / (totalFrames - 1) : 0.0;
    const timestamp = i * timeStepSec;
    const padded = String(i).padStart(4, '0');
    const filename = `${outputDir}/${prefix}${padded}.png`;

    valuesRows.push([
      generateUuidV4(),
      i,
      parseFloat(progress.toFixed(6)),
      parseFloat(timestamp.toFixed(4)),
      filename,
      false,
      ''
    ]);
  }

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Records_Type: ['CanvasFrameSequence'],
    Fields: CANVAS_FRAME_SEQUENCE_FIELDS.map(f => ({ ...f })),
    Values: valuesRows
  };
}

function computeFrameSeekPoints(durationSec, fps, framesCount = null) {
  if (!framesCount || framesCount <= 0) {
    framesCount = Math.max(1, Math.ceil(durationSec * fps));
  }
  const stepRatio = framesCount > 1 ? 1.0 / (framesCount - 1) : 0.0;
  const timeStep = framesCount > 1 ? durationSec / (framesCount - 1) : 0.0;

  const points = [];
  for (let i = 0; i < framesCount; i++) {
    const ratio = Math.min(1.0, Math.max(0.0, i * stepRatio));
    const timestamp = Math.min(durationSec, i * timeStep);
    points.push({
      frameIndex: i,
      seekProgress: parseFloat(ratio.toFixed(6)),
      timestampSec: parseFloat(timestamp.toFixed(4))
    });
  }
  return points;
}

function validateCanvasConfig(doc) {
  const errors = [];
  if (!doc || typeof doc !== 'object') {
    return { valid: false, errors: ['Root is not an object'] };
  }
  if (doc.Format !== 'BEJSON') errors.push("Format must be 'BEJSON'");
  if (doc.Format_Version !== '105' && doc.Format_Version !== '105a') {
    errors.push("Format_Version must be '105' or '105a'");
  }
  if (!Array.isArray(doc.Fields) || doc.Fields.length < CANVAS_STUDIO_CONFIG_FIELDS.length) {
    errors.push('Missing required Fields array');
  }
  if (!Array.isArray(doc.Values) || doc.Values.length === 0) {
    errors.push('Values array must have at least one row');
  }
  return { valid: errors.length === 0, errors };
}

function getConfigDict(doc, rowIdx = 0) {
  if (!doc.Values || rowIdx >= doc.Values.length) {
    throw new RangeError(`Row index ${rowIdx} out of range`);
  }
  const row = doc.Values[rowIdx];
  const fieldMap = buildFieldMap105(doc.Fields);
  const result = { record_uuid: row[0] };
  for (const [name, colIdx] of Object.entries(fieldMap)) {
    result[name] = row[colIdx];
  }
  return result;
}

const moduleExports = {
  CANVAS_STUDIO_CONFIG_FIELDS,
  CANVAS_FRAME_SEQUENCE_FIELDS,
  buildFieldMap105,
  createCanvasConfig105a,
  createFrameSequence105a,
  computeFrameSeekPoints,
  validateCanvasConfig,
  getConfigDict
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = moduleExports;
}
if (typeof window !== 'undefined') {
  window.lib_bejson_Canvas_canvas_schemas = moduleExports;
}
