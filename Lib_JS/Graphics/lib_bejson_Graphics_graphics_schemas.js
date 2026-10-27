/**
 * Library:        lib_bejson_Graphics_graphics_schemas.js
 * Family:         Graphics
 * Description:    BEJSON 105a Schemas for Blank-Slate Stages, Dynamic Frames & Row-Per-Frame Animations.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.0
 * Release_Version: 300
 */

'use strict';

const crypto = require('crypto');

function generateUuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

const GRAPHIC_CANVAS_CONFIG_FIELDS = [
  { name: 'canvas_id',          type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000001' },
  { name: 'template_name',      type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000002' },
  { name: 'stage_selector',     type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000003' },
  { name: 'width_px',           type: 'integer', field_uuid: '9a1b2c3d-1111-4000-8000-000000000004' },
  { name: 'height_px',          type: 'integer', field_uuid: '9a1b2c3d-1111-4000-8000-000000000005' },
  { name: 'aspect_ratio',       type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000006' },
  { name: 'bg_theme',           type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000007' },
  { name: 'accent_color',       type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000008' },
  { name: 'device_scale',       type: 'integer', field_uuid: '9a1b2c3d-1111-4000-8000-000000000009' },
  { name: 'output_dir',         type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000010' },
  { name: 'text_overlays_json', type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000011' }
];

const GRAPHIC_ROW_FRAME_FIELDS = [
  { name: 'frame_index',      type: 'integer', field_uuid: '9b2c3d4e-2222-4000-8000-000000000001' },
  { name: 'timestamp_sec',    type: 'number',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000002' },
  { name: 'seek_progress',    type: 'number',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000003' },
  { name: 'fps',              type: 'integer', field_uuid: '9b2c3d4e-2222-4000-8000-000000000004' },
  { name: 'frame_filename',   type: 'string',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000005' },
  { name: 'svg_markup',       type: 'string',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000006' },
  { name: 'frame_data_json',  type: 'string',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000007' },
  { name: 'is_rendered',      type: 'boolean', field_uuid: '9b2c3d4e-2222-4000-8000-000000000008' },
  { name: 'checksum_sha256',  type: 'string',  field_uuid: '9b2c3d4e-2222-4000-8000-000000000009' }
];

const GRAPHIC_TEMPLATE_REGISTRY_FIELDS = [
  { name: 'template_id',      type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000001' },
  { name: 'template_name',    type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000002' },
  { name: 'category',         type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000003' },
  { name: 'width_px',         type: 'integer', field_uuid: '9c3d4e5f-3333-4000-8000-000000000004' },
  { name: 'height_px',        type: 'integer', field_uuid: '9c3d4e5f-3333-4000-8000-000000000005' },
  { name: 'aspect_ratio',     type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000006' },
  { name: 'stage_selector',   type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000007' },
  { name: 'description',      type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000008' },
  { name: 'html_template',    type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000009' },
  { name: 'checksum_sha256',  type: 'string',  field_uuid: '9c3d4e5f-3333-4000-8000-000000000010' }
];

function buildFieldMap105(fields) {
  const map = {};
  fields.forEach((f, idx) => {
    map[f.name] = idx + 1;
  });
  return map;
}

function createCoordinateTextOverlay(options = {}) {
  return {
    x: options.x !== undefined ? options.x : 20,
    y: options.y !== undefined ? options.y : 20,
    text: options.text || '',
    font_size: Number(options.font_size || 20),
    font_family: options.font_family || 'monospace',
    font_weight: options.font_weight || 'bold',
    color: options.color || '#FFFFFF',
    bg_color: options.bg_color !== undefined ? options.bg_color : 'rgba(0, 0, 0, 0.75)',
    padding: options.padding || '4px 10px',
    border_radius: options.border_radius || '4px',
    align: options.align || 'left',
    opacity: options.opacity !== undefined ? Number(options.opacity) : 1.0,
    z_index: options.z_index !== undefined ? Number(options.z_index) : 100
  };
}

function createGraphicStageConfig105a(options = {}) {
  const recUuid = generateUuid();
  const overlays = options.text_overlays ? JSON.stringify(options.text_overlays) : '[]';
  const row = [
    recUuid,
    options.canvas_id || 'stage_blank_01',
    options.template_name || 'blank_slate_stage.html',
    options.stage_selector || '#capture-stage',
    Number(options.width_px || 800),
    Number(options.height_px || 800),
    options.aspect_ratio || '1:1',
    options.bg_theme || '#000000',
    options.accent_color || '#DE2626',
    Number(options.device_scale || 2),
    options.output_dir || 'captures/stage',
    overlays
  ];

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Record_Type: ['GraphicCanvasConfig'],
    Fields: GRAPHIC_CANVAS_CONFIG_FIELDS.map(f => Object.assign({}, f)),
    Values: [row]
  };
}

function createRowPerFrameAnimation105a(options = {}) {
  const durationSec = Number(options.duration_sec || 8.0);
  const fps = Number(options.fps || 30);
  const totalFrames = Math.max(1, Math.ceil(durationSec * fps));
  const timeStepSec = totalFrames > 1 ? durationSec / (totalFrames - 1) : 0.0;
  const outputPrefix = options.output_prefix || 'frame_';
  const dynamicFrames = options.dynamic_frames || [];

  const valuesRows = [];
  for (let idx = 0; idx < totalFrames; idx++) {
    const recUuid = generateUuid();
    const ts = Number((idx * timeStepSec).toFixed(6));
    const progress = totalFrames > 1 ? Number((idx / (totalFrames - 1)).toFixed(6)) : 0.0;
    const filename = `${outputPrefix}${String(idx).padStart(4, '0')}.png`;

    let svgMarkup = '';
    let frameDataJson = '{}';
    if (idx < dynamicFrames.length) {
      svgMarkup = dynamicFrames[idx].svg_markup || '';
      if (dynamicFrames[idx].data) {
        frameDataJson = JSON.stringify(dynamicFrames[idx].data);
      }
    }

    valuesRows.push([
      recUuid,
      idx,
      ts,
      progress,
      fps,
      filename,
      svgMarkup,
      frameDataJson,
      false,
      ''
    ]);
  }

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Animation_Name: options.animation_name || 'graphic_anim',
    Duration_Sec: durationSec,
    FPS: fps,
    Total_Frames: totalFrames,
    Width_Px: Number(options.width_px || 800),
    Height_Px: Number(options.height_px || 800),
    Aspect_Ratio: options.aspect_ratio || '1:1',
    Canvas_Id: options.canvas_id || 'canvas_anim_01',
    Template_Name: options.template_name || 'blank_slate_stage.html',
    Record_Type: ['GraphicFrameRecord'],
    Fields: GRAPHIC_ROW_FRAME_FIELDS.map(f => Object.assign({}, f)),
    Values: valuesRows
  };
}

function validateGraphic105aDoc(doc) {
  const errors = [];
  if (!doc || doc.Format !== 'BEJSON') errors.push("Format must be 'BEJSON'");
  if (!doc || !['105', '105a', '105db'].includes(doc.Format_Version)) errors.push("Format_Version must be 105-series");
  if (!doc || !Array.isArray(doc.Fields) || doc.Fields.length === 0) errors.push('Fields array is missing or empty');
  if (!doc || !Array.isArray(doc.Values)) errors.push('Values is not an array');
  return { valid: errors.length === 0, errors };
}

module.exports = {
  GRAPHIC_CANVAS_CONFIG_FIELDS,
  GRAPHIC_ROW_FRAME_FIELDS,
  GRAPHIC_TEMPLATE_REGISTRY_FIELDS,
  buildFieldMap105,
  createCoordinateTextOverlay,
  createGraphicStageConfig105a,
  createRowPerFrameAnimation105a,
  validateGraphic105aDoc
};
