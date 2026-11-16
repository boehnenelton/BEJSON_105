/**
 * Library:        lib_bejson_Gaming_Editors_schemas.js
 * Family:         Gaming_Editors (libraries_105)
 * Description:    BEJSON 105a Schema Definitions and O(1) Field Map Caching for Game Editors.
 * Version:        1.0.0
 * Date:           2026-11-15
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * License:        PolyForm-Noncommercial-1.0.0
 * RELATIONAL_ID:  8c0b2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e
 * Release_Version: 300
 */

'use strict';

const crypto = require('crypto');

const GAMING_SPRITE_STUDIO_FIELDS = [
  { name: 'editor_id',      type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000001' },
  { name: 'template_name',  type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000002' },
  { name: 'canvas_size_px', type: 'integer', field_uuid: 'c1a2b3c4-1111-4000-8000-000000000003' },
  { name: 'cell_size_px',   type: 'integer', field_uuid: 'c1a2b3c4-1111-4000-8000-000000000004' },
  { name: 'grid_rows',      type: 'integer', field_uuid: 'c1a2b3c4-1111-4000-8000-000000000005' },
  { name: 'grid_cols',      type: 'integer', field_uuid: 'c1a2b3c4-1111-4000-8000-000000000006' },
  { name: 'bg_theme',       type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000007' },
  { name: 'accent_color',   type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000008' },
  { name: 'show_grid',      type: 'boolean', field_uuid: 'c1a2b3c4-1111-4000-8000-000000000009' },
  { name: 'cells_json',     type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000010' },
  { name: 'output_path',    type: 'string',  field_uuid: 'c1a2b3c4-1111-4000-8000-000000000011' }
];

const GAMING_TILEMAP_PALETTE_FIELDS = [
  { name: 'palette_id',     type: 'string',  field_uuid: 'c2a3b4c5-2222-4000-8000-000000000001' },
  { name: 'template_name',  type: 'string',  field_uuid: 'c2a3b4c5-2222-4000-8000-000000000002' },
  { name: 'canvas_size_px', type: 'integer', field_uuid: 'c2a3b4c5-2222-4000-8000-000000000003' },
  { name: 'tile_size_px',   type: 'integer', field_uuid: 'c2a3b4c5-2222-4000-8000-000000000004' },
  { name: 'palette_rows',   type: 'integer', field_uuid: 'c2a3b4c5-2222-4000-8000-000000000005' },
  { name: 'palette_cols',   type: 'integer', field_uuid: 'c2a3b4c5-2222-4000-8000-000000000006' },
  { name: 'show_collision', type: 'boolean', field_uuid: 'c2a3b4c5-2222-4000-8000-000000000007' },
  { name: 'tiles_json',     type: 'string',  field_uuid: 'c2a3b4c5-2222-4000-8000-000000000008' },
  { name: 'output_path',    type: 'string',  field_uuid: 'c2a3b4c5-2222-4000-8000-000000000009' }
];

const GAMING_HUD_STAGE_FIELDS = [
  { name: 'hud_id',            type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000001' },
  { name: 'template_name',     type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000002' },
  { name: 'width_px',          type: 'integer', field_uuid: 'c3a4b5c6-3333-4000-8000-000000000003' },
  { name: 'height_px',         type: 'integer', field_uuid: 'c3a4b5c6-3333-4000-8000-000000000004' },
  { name: 'aspect_ratio',      type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000005' },
  { name: 'max_hearts',        type: 'integer', field_uuid: 'c3a4b5c6-3333-4000-8000-000000000006' },
  { name: 'current_hearts',    type: 'number',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000007' },
  { name: 'has_magic_gauge',   type: 'boolean', field_uuid: 'c3a4b5c6-3333-4000-8000-000000000008' },
  { name: 'item_slots_json',   type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000009' },
  { name: 'dialog_state_json', type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000010' },
  { name: 'output_path',       type: 'string',  field_uuid: 'c3a4b5c6-3333-4000-8000-000000000011' }
];

function buildFieldMap105(fields) {
  const fieldMap = { record_uuid: 0 };
  const list = Array.isArray(fields) ? fields : (fields && fields.Fields ? fields.Fields : []);
  for (let i = 0; i < list.length; i++) {
    fieldMap[list[i].name] = i + 1;
  }
  return fieldMap;
}

function createSpriteStudioConfig105a(options = {}) {
  const canvasSize = options.canvas_size_px || 512;
  const cellSize = options.cell_size_px || 32;
  const rows = Math.floor(canvasSize / cellSize);
  const cols = Math.floor(canvasSize / cellSize);

  const row = [
    crypto.randomUUID(),
    options.editor_id || 'sprite_studio_01',
    options.template_name || 'template_game_sprite_sheet_studio.html',
    canvasSize,
    cellSize,
    rows,
    cols,
    options.bg_theme || '#000000',
    options.accent_color || '#DE2626',
    options.show_grid !== false,
    JSON.stringify(options.cells_data || []),
    options.output_path || 'captures/game_sprite_sheet_512x512.png'
  ];

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Records_Type: ['GamingSpriteStudioConfig'],
    Fields: GAMING_SPRITE_STUDIO_FIELDS.map(f => Object.assign({}, f)),
    Values: [row]
  };
}

const PROJECTILE_IMPACT_DYNAMICS_FIELDS = [
  { name: 'record_uuid', type: 'uuid' },
  { name: 'object_type', type: 'string' },
  { name: 'surface_hardness', type: 'float' },
  { name: 'penetration_behavior', type: 'string' },
  { name: 'damage_multiplier', type: 'float' },
  { name: 'splash_particle_count', type: 'int' },
  { name: 'kinetic_recoil_factor', type: 'float' },
  { name: 'primary_particle_color', type: 'string' },
  { name: 'secondary_particle_color', type: 'string' },
  { name: 'impact_vfx_preset', type: 'string' },
  { name: 'sound_cue_id', type: 'string' },
  { name: 'quiver_vibration_ms', type: 'int' },
  { name: 'status_debuff_inflicted', type: 'string' }
];

function createProjectileImpactRegistry105a(entries) {
  const fieldMap = buildFieldMap105(PROJECTILE_IMPACT_DYNAMICS_FIELDS);
  const data = entries || [
    {
      object_type: 'flesh_organic',
      surface_hardness: 0.15,
      penetration_behavior: 'embed',
      damage_multiplier: 1.5,
      splash_particle_count: 24,
      kinetic_recoil_factor: 0.1,
      primary_particle_color: '#DE2626',
      secondary_particle_color: '#000000',
      impact_vfx_preset: 'vfx_puncture_bleed',
      sound_cue_id: 'sfx_flesh_pierce_01',
      quiver_vibration_ms: 200,
      status_debuff_inflicted: 'bleed_slow'
    },
    {
      object_type: 'stone_masonry',
      surface_hardness: 0.90,
      penetration_behavior: 'shatter',
      damage_multiplier: 0.25,
      splash_particle_count: 18,
      kinetic_recoil_factor: 0.7,
      primary_particle_color: '#FFFFFF',
      secondary_particle_color: '#64748B',
      impact_vfx_preset: 'vfx_flint_shatter',
      sound_cue_id: 'sfx_stone_chink_01',
      quiver_vibration_ms: 0,
      status_debuff_inflicted: 'none'
    }
  ];

  const rows = data.map((e, idx) => {
    const row = new Array(PROJECTILE_IMPACT_DYNAMICS_FIELDS.length).fill(null);
    row[fieldMap['record_uuid']] = `a0110001-${String(idx + 1).padStart(4, '0')}-4000-8000-${String(idx + 1).padStart(12, '0')}`;
    row[fieldMap['object_type']] = String(e.object_type || 'unknown');
    row[fieldMap['surface_hardness']] = Number(e.surface_hardness || 0.5);
    row[fieldMap['penetration_behavior']] = String(e.penetration_behavior || 'embed');
    row[fieldMap['damage_multiplier']] = Number(e.damage_multiplier || 1.0);
    row[fieldMap['splash_particle_count']] = Number(e.splash_particle_count || 10);
    row[fieldMap['kinetic_recoil_factor']] = Number(e.kinetic_recoil_factor || 0.5);
    row[fieldMap['primary_particle_color']] = String(e.primary_particle_color || '#FFFFFF');
    row[fieldMap['secondary_particle_color']] = String(e.secondary_particle_color || '#000000');
    row[fieldMap['impact_vfx_preset']] = String(e.impact_vfx_preset || 'default');
    row[fieldMap['sound_cue_id']] = String(e.sound_cue_id || 'default');
    row[fieldMap['quiver_vibration_ms']] = Number(e.quiver_vibration_ms || 0);
    row[fieldMap['status_debuff_inflicted']] = String(e.status_debuff_inflicted || 'none');
    return row;
  });

  return {
    Format: 'BEJSON',
    Format_Version: '105a',
    Format_Creator: 'Elton Boehnen',
    Records_Type: ['ProjectileImpactDynamics'],
    Schema_Name: 'Projectile_Impact_Dynamics_Registry',
    Schema_Version: '10501',
    Fields: PROJECTILE_IMPACT_DYNAMICS_FIELDS.map(f => Object.assign({}, f)),
    Values: rows
  };
}

module.exports = {
  GAMING_SPRITE_STUDIO_FIELDS,
  GAMING_TILEMAP_PALETTE_FIELDS,
  GAMING_HUD_STAGE_FIELDS,
  PROJECTILE_IMPACT_DYNAMICS_FIELDS,
  buildFieldMap105,
  createSpriteStudioConfig105a,
  createProjectileImpactRegistry105a,
  Build_Field_Map_105: buildFieldMap105,
  Create_Sprite_Studio_Config_105a: createSpriteStudioConfig105a,
  Create_Projectile_Impact_Registry_105a: createProjectileImpactRegistry105a
};

