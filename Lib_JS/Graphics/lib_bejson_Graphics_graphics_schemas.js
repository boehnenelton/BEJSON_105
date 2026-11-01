/**
 * Library:        lib_bejson_Graphics_graphics_schemas.js
 * Family:         Graphics
 * Description:    BEJSON 105a Schemas for Blank-Slate Stages, Dynamic Frames & Row-Per-Frame Animations.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.1
 * Date:           2026-10-30
 * Changelog:
 *   1.0.1 - 2026-10-30: Records_Type key fix (was Record_Type).
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
  { name: 'text_overlays_json', type: 'string',  field_uuid: '9a1b2c3d-1111-4000-8000-000000000011' },
  { name: 'remove_frame_source', type: 'boolean', field_uuid: '9a1b2c3d-1111-4000-8000-000000000012' }
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

const GRAPHIC_ANIMATION_TIMELINE_FIELDS = [
  { name: 'frame_index',       type: 'integer', field_uuid: '9d4e5f6a-4444-4000-8000-000000000001' },
  { name: 'timestamp_ms',      type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000002' },
  { name: 'frame_duration_ms', type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000003' },
  { name: 'fps',               type: 'integer', field_uuid: '9d4e5f6a-4444-4000-8000-000000000004' },
  { name: 'seek_progress',     type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000005' },
  { name: 'rotation_deg',      type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000006' },
  { name: 'scale_factor',      type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000007' },
  { name: 'opacity',           type: 'number',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000008' },
  { name: 'svg_markup',        type: 'string',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000009' },
  { name: 'frame_filename',    type: 'string',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000010' },
  { name: 'is_rendered',       type: 'boolean', field_uuid: '9d4e5f6a-4444-4000-8000-000000000011' },
  { name: 'checksum_sha256',   type: 'string',  field_uuid: '9d4e5f6a-4444-4000-8000-000000000012' }
];

const GRAPHIC_SLIDE_FIELDS = [
  { name: 'slide_index',         type: 'integer', field_uuid: '9f6a7b8c-6666-4000-8000-000000000001' },
  { name: 'slide_type',          type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000002' },
  { name: 'title',               type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000003' },
  { name: 'subtitle',            type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000004' },
  { name: 'duration_sec',        type: 'number',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000005' },
  { name: 'timestamp_sec',       type: 'number',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000006' },
  { name: 'width_px',            type: 'integer', field_uuid: '9f6a7b8c-6666-4000-8000-000000000007' },
  { name: 'height_px',           type: 'integer', field_uuid: '9f6a7b8c-6666-4000-8000-000000000008' },
  { name: 'svg_markup',          type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000009' },
  { name: 'slide_filename',      type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000010' },
  { name: 'is_rendered',         type: 'boolean', field_uuid: '9f6a7b8c-6666-4000-8000-000000000011' },
  { name: 'checksum_sha256',     type: 'string',  field_uuid: '9f6a7b8c-6666-4000-8000-000000000012' },
  { name: 'remove_frame_source', type: 'boolean', field_uuid: '9f6a7b8c-6666-4000-8000-000000000013' }
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

const GRAPHIC_MFDB_MANIFEST_FIELDS = [
  { name: 'entity_name',    type: 'string',  field_uuid: '9e5f6a7b-5555-4000-8000-000000000001' },
  { name: 'file_path',      type: 'string',  field_uuid: '9e5f6a7b-5555-4000-8000-000000000002' },
  { name: 'description',    type: 'string',  field_uuid: '9e5f6a7b-5555-4000-8000-000000000003' },
  { name: 'record_count',   type: 'integer', field_uuid: '9e5f6a7b-5555-4000-8000-000000000004' },
  { name: 'schema_version', type: 'string',  field_uuid: '9e5f6a7b-5555-4000-8000-000000000005' },
  { name: 'primary_key',    type: 'string',  field_uuid: '9e5f6a7b-5555-4000-8000-000000000006' }
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
    overlays,
    Boolean(options.remove_frame_source)
  ];

  const doc = {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Remove_Frame_Source: Boolean(options.remove_frame_source),
    Records_Type: ['GraphicCanvasConfig'],
    Fields: GRAPHIC_CANVAS_CONFIG_FIELDS.map(f => Object.assign({}, f)),
    Values: [row]
  };
  if (options.parent_hierarchy) {
    doc.Parent_Hierarchy = options.parent_hierarchy;
  }
  return doc;
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

  const doc = {
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
    Remove_Frame_Source: Boolean(options.remove_frame_source),
    Records_Type: ['GraphicFrameRecord'],
    Fields: GRAPHIC_ROW_FRAME_FIELDS.map(f => Object.assign({}, f)),
    Values: valuesRows
  };
  if (options.parent_hierarchy) {
    doc.Parent_Hierarchy = options.parent_hierarchy;
  }
  return doc;
}

function createSvgAnimationTimeline105a(options = {}) {
  const fps = Number(options.fps || 24);
  const totalFrames = Number(options.total_frames || 24);
  const totalDurationMs = Math.round((totalFrames / fps) * 1000);
  const durationPerFrameMs = Number((totalDurationMs / totalFrames).toFixed(2));
  const outputPrefix = options.output_prefix || 'frame_';
  const dynamicFrames = options.dynamic_frames || [];

  const valuesRows = [];
  for (let idx = 0; idx < totalFrames; idx++) {
    const recUuid = generateUuid();
    const tsMs = Number((idx * durationPerFrameMs).toFixed(2));
    const progress = Number((idx / Math.max(1, totalFrames)).toFixed(4));
    let rotDeg = Number((idx * (360.0 / totalFrames)).toFixed(2));
    let scaleFactor = 1.0;
    let opacity = 1.0;
    let svgMarkup = '';

    if (idx < dynamicFrames.length) {
      const f = dynamicFrames[idx];
      svgMarkup = f.svg_markup || '';
      if (f.rotation_deg !== undefined) rotDeg = f.rotation_deg;
      if (f.scale_factor !== undefined) scaleFactor = f.scale_factor;
      if (f.opacity !== undefined) opacity = f.opacity;
    }

    const sha256 = svgMarkup ? crypto.createHash('sha256').update(svgMarkup).digest('hex') : '';
    valuesRows.push([
      recUuid,
      idx,
      tsMs,
      durationPerFrameMs,
      fps,
      progress,
      rotDeg,
      scaleFactor,
      opacity,
      svgMarkup,
      `${outputPrefix}${String(idx).padStart(4, '0')}.png`,
      Boolean(svgMarkup),
      sha256
    ]);
  }

  const doc = {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Animation_Name: options.animation_name || 'timeline_anim',
    Total_Duration_Ms: totalDurationMs,
    FPS: fps,
    Total_Frames: totalFrames,
    Width_Px: Number(options.width_px || 400),
    Height_Px: Number(options.height_px || 400),
    Aspect_Ratio: options.aspect_ratio || '1:1',
    Remove_Frame_Source: Boolean(options.remove_frame_source),
    Records_Type: ['SvgAnimationTimelineRecord'],
    Fields: GRAPHIC_ANIMATION_TIMELINE_FIELDS.map(f => Object.assign({}, f)),
    Values: valuesRows
  };
  if (options.parent_hierarchy) {
    doc.Parent_Hierarchy = options.parent_hierarchy;
  }
  return doc;
}

function createGraphicsMfdbManifest105a(options = {}) {
  const entities = options.entities || [];
  const nowIso = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  const valuesRows = entities.map(ent => [
    generateUuid(),
    ent.entity_name || '',
    ent.file_path || '',
    ent.description || '',
    Number(ent.record_count || 0),
    ent.schema_version || '1.0.0',
    ent.primary_key || 'record_uuid'
  ]);

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    MFDB_Version: '1.40',
    DB_Name: options.db_name || 'Graphics_Animation_Studio',
    DB_Description: options.db_description || 'Graphics Domain Animation & Stage MFDB',
    Schema_Version: '1.0.0',
    Author: options.author || 'Elton Boehnen',
    Created_At: nowIso,
    Modified_At: nowIso,
    Network_Role: 'Master',
    Remove_Frame_Source: Boolean(options.remove_frame_source),
    Records_Type: ['mfdb'],
    Fields: GRAPHIC_MFDB_MANIFEST_FIELDS.map(f => Object.assign({}, f)),
    Values: valuesRows
  };
}

function createBrandingSlideDeck105a(options) {
  options = options || {};
  const slides = options.slides || [];
  const defaultDur = options.default_duration_sec || 3.0;
  const widthPx = options.width_px || 1280;
  const heightPx = options.height_px || 720;
  const aspectRatio = options.aspect_ratio || '16:9';
  const deckName = options.deck_name || 'BrandingSlideDeck';
  const removeFrameSource = Boolean(options.remove_frame_source);
  const isEntityTable = Boolean(options.is_entity_table);

  let totalDuration = 0.0;
  const fMap = buildFieldMap105(GRAPHIC_SLIDE_FIELDS);
  const valuesRows = [];

  slides.forEach((slide, sIdx) => {
    const dur = typeof slide.duration_sec === 'number' ? slide.duration_sec : defaultDur;
    const sType = slide.slide_type || 'branding_slide';
    const title = slide.title || `Slide ${sIdx + 1}`;
    const subtitle = slide.subtitle || '';
    const svg = slide.svg_markup || '';
    const fn = slide.slide_filename || `slide_${String(sIdx).padStart(2, '0')}_${sType}.svg`;
    const cHash = slide.checksum_sha256 || (svg ? crypto.createHash('sha256').update(svg).digest('hex') : '');
    const recUuid = generateUuid();

    const row = new Array(GRAPHIC_SLIDE_FIELDS.length + 1).fill(null);
    row[0] = recUuid;
    row[fMap.slide_index] = sIdx;
    row[fMap.slide_type] = sType;
    row[fMap.title] = title;
    row[fMap.subtitle] = subtitle;
    row[fMap.duration_sec] = dur;
    row[fMap.timestamp_sec] = Math.round(totalDuration * 1000) / 1000;
    row[fMap.width_px] = widthPx;
    row[fMap.height_px] = heightPx;
    row[fMap.svg_markup] = svg;
    row[fMap.slide_filename] = fn;
    row[fMap.is_rendered] = Boolean(slide.is_rendered);
    row[fMap.checksum_sha256] = cHash;
    row[fMap.remove_frame_source] = removeFrameSource;
    valuesRows.append ? valuesRows.append(row) : valuesRows.push(row);
    totalDuration += dur;
  });

  if (isEntityTable) {
    const entityDoc = {
      Format: 'BEJSON',
      Format_Version: '105',
      Format_Creator: 'Elton Boehnen',
      Records_Type: [deckName],
      Fields: GRAPHIC_SLIDE_FIELDS.map(f => Object.assign({}, f)),
      Values: valuesRows
    };
    if (options.parent_hierarchy) entityDoc.Parent_Hierarchy = options.parent_hierarchy;
    return entityDoc;
  }

  const deckDoc = {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Deck_Name: deckName,
    Total_Slides: slides.length,
    Total_Duration_Sec: Math.round(totalDuration * 1000) / 1000,
    Width_Px: widthPx,
    Height_Px: heightPx,
    Aspect_Ratio: aspectRatio,
    Remove_Frame_Source: removeFrameSource,
    Records_Type: ['GraphicSlideRecord'],
    Fields: GRAPHIC_SLIDE_FIELDS.map(f => Object.assign({}, f)),
    Values: valuesRows
  };
  if (options.parent_hierarchy) deckDoc.Parent_Hierarchy = options.parent_hierarchy;
  return deckDoc;
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
  GRAPHIC_ANIMATION_TIMELINE_FIELDS,
  GRAPHIC_SLIDE_FIELDS,
  GRAPHIC_TEMPLATE_REGISTRY_FIELDS,
  GRAPHIC_MFDB_MANIFEST_FIELDS,
  buildFieldMap105,
  createCoordinateTextOverlay,
  createGraphicStageConfig105a,
  createRowPerFrameAnimation105a,
  createSvgAnimationTimeline105a,
  createBrandingSlideDeck105a,
  createGraphicsMfdbManifest105a,
  validateGraphic105aDoc
};
