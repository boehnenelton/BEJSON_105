/**
 * Library:        lib_bejson_Gaming_Editors_templates.js
 * Family:         Gaming_Editors (libraries_105)
 * Description:    Template catalog for Gaming_Editors 105 Family.
 * Version:        1.0.0
 * Date:           2026-11-15
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * License:        PolyForm-Noncommercial-1.0.0
 * RELATIONAL_ID:  ae2d4f5a-6b7c-8d9e-0f1a-2b3c4d5e6f7a
 * Release_Version: 300
 */

'use strict';

const GAMING_EDITOR_TEMPLATES_CATALOG = [
  {
    template_id: 'game_sprite_sheet_studio_512',
    template_name: 'template_game_sprite_sheet_studio.html',
    category: 'gaming_editor',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    stage_selector: '#capture-stage',
    bg_theme: '#000000',
    description: '512x512 Game Sprite Sheet Studio blank-slate stage with 16/32/48/64px cells, pivot reticles, window.setCellSvg(r,c,svg), and #isolated-cell export.'
  },
  {
    template_id: 'game_sprite_animation_stage_400',
    template_name: 'template_game_sprite_animation_stage.html',
    category: 'gaming_editor',
    width_px: 400,
    height_px: 400,
    aspect_ratio: '1:1',
    stage_selector: '#capture-stage',
    bg_theme: '#000000',
    description: '400x400 Game Sprite Animation Stage with 2x/4x/8x zoom, onion skinning ghost layer, 4-frame pill strip, and window.setAnimationFrames(frames,label).'
  },
  {
    template_id: 'game_tilemap_palette_stage_512',
    template_name: 'template_game_tilemap_palette_stage.html',
    category: 'gaming_editor',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    stage_selector: '#capture-stage',
    bg_theme: '#000000',
    description: '512x512 Game Tilemap Palette Stage with 16/32/64px tiles, solid/passable collision badges (X/O), window.setTileSvg(r,c,svg,solid), and #isolated-tile export.'
  },
  {
    template_id: 'game_hud_ui_stage_640',
    template_name: 'template_game_hud_ui_stage.html',
    category: 'gaming_editor',
    width_px: 640,
    height_px: 480,
    aspect_ratio: '4:3',
    stage_selector: '#capture-stage',
    bg_theme: '#000000',
    description: '640x480 Game HUD & UI Stage with hearts, MP gauge, B/Y active item boxes, virtual gamepad controls, dialog letterbox, and #isolated-element export.'
  }
];

function listGamingEditorTemplates() {
  return GAMING_EDITOR_TEMPLATES_CATALOG.map(t => Object.assign({}, t));
}

module.exports = {
  GAMING_EDITOR_TEMPLATES_CATALOG,
  listGamingEditorTemplates,
  List_Gaming_Editor_Templates: listGamingEditorTemplates
};
