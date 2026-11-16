/**
 * Library:        lib_bejson_Graphics_graphics_canvas_templates.js
 * Family:         Graphics
 * Description:    Blank-Slate Canvas Stage Templates in JavaScript for BEJSON 105a.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.1
 * Changelog:      1.0.1 (2026-11-12) header: RELATIONAL_ID recency fingerprint added (code unchanged)
 * RELATIONAL_ID:  7d531a14-97b4-4a60-a119-0dea64be150c
 * Release_Version: 300
 */

'use strict';

function generateBlankSlateHtml(options = {}) {
  const widthPx = Number(options.width_px || 800);
  const heightPx = Number(options.height_px || 800);
  const bgTheme = options.bg_theme || '#000000';
  const title = options.title || 'Blank Slate Canvas Stage';
  const initialSvg = options.initial_svg_markup || `
    <svg id="dynamic-svg" viewBox="0 0 ${widthPx} ${heightPx}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block;">
      <!-- Dynamic Blank Slate Canvas -->
    </svg>
  `;

  const borderCss = bgTheme === 'transparent' ? 'none' : '1px solid #1c1c24';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100vw; height: 100vh;
      background: ${bgTheme};
      display: flex; align-items: center; justify-content: center;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    }
    #capture-stage {
      position: relative;
      width: ${widthPx}px; height: ${heightPx}px;
      background: ${bgTheme};
      border: ${borderCss};
      overflow: hidden;
      display: flex; align-items: center; justify-content: center;
    }
    .canvas-slot {
      width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
      position: relative;
    }
    .canvas-slot > svg, .canvas-slot > img {
      width: 100%; height: 100%;
      display: block; object-fit: contain;
    }
  </style>
</head>
<body>
  <div id="capture-stage" data-width="${widthPx}" data-height="${heightPx}">
    <div class="canvas-slot" id="stage-slot">
      ${initialSvg}
    </div>
    <!-- Pre-recording Coordinate-Based Text Overlay Layer -->
    <div id="overlay-layer" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:100;overflow:hidden;"></div>
  </div>

  <script>
    window.isReadyToCapture = true;
    window._activeOverlays = [];

    window.setSvgContent = function(svgMarkup) {
      const slot = document.getElementById('stage-slot');
      if (slot) {
        slot.innerHTML = svgMarkup;
        window.isReadyToCapture = true;
      }
    };

    window.setDimensions = function(width, height) {
      const stage = document.getElementById('capture-stage');
      if (stage) {
        stage.style.width = width + 'px';
        stage.style.height = height + 'px';
        stage.setAttribute('data-width', width);
        stage.setAttribute('data-height', height);
      }
    };

    window.setTextOverlays = function(overlays, context) {
      const layer = document.getElementById('overlay-layer');
      if (!layer) return;
      layer.innerHTML = '';
      window._activeOverlays = overlays || [];
      const ctx = context || {};

      (window._activeOverlays).forEach(o => {
        const item = document.createElement('div');
        item.style.position = 'absolute';
        item.style.left = typeof o.x === 'number' ? o.x + 'px' : o.x;
        item.style.top = typeof o.y === 'number' ? o.y + 'px' : o.y;
        item.style.fontSize = (o.font_size || 20) + 'px';
        item.style.fontFamily = o.font_family || 'monospace';
        item.style.fontWeight = o.font_weight || 'bold';
        item.style.color = o.color || '#FFFFFF';
        if (o.bg_color) item.style.backgroundColor = o.bg_color;
        if (o.padding) item.style.padding = o.padding;
        if (o.border_radius) item.style.borderRadius = o.border_radius;
        if (o.opacity !== undefined) item.style.opacity = o.opacity;
        if (o.z_index) item.style.zIndex = o.z_index;
        if (o.align) item.style.textAlign = o.align;

        let rawText = o.text || '';
        rawText = rawText.replace(/{frame}/g, ctx.frame !== undefined ? ctx.frame : '')
                         .replace(/{time}/g, ctx.time !== undefined ? Number(ctx.time).toFixed(2) : '')
                         .replace(/{fps}/g, ctx.fps || '')
                         .replace(/{caption}/g, ctx.caption || '');
        item.textContent = rawText;
        layer.appendChild(item);
      });
      window.isReadyToCapture = true;
    };

    window.seekProgress = function(progress, durationSeconds) {
      const dur = durationSeconds || 8.0;
      const targetTimeSec = progress * dur;
      document.querySelectorAll('#capture-stage *').forEach(el => {
        el.style.animationDelay = '-' + targetTimeSec + 's';
        el.style.animationPlayState = 'paused';
      });
    };
  </script>
</body>
</html>
`;
}

const GAME_STAGE_ARCHETYPES = [
  {
    template_id: 'game_sprite_sheet_studio_512',
    template_name: 'template_game_sprite_sheet_studio.html',
    category: 'game_stage',
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
    category: 'game_stage',
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
    category: 'game_stage',
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
    category: 'game_stage',
    width_px: 640,
    height_px: 480,
    aspect_ratio: '4:3',
    stage_selector: '#capture-stage',
    bg_theme: '#000000',
    description: '640x480 Game HUD & UI Stage with hearts, MP gauge, B/Y active item boxes, virtual gamepad controls, dialog letterbox, and #isolated-element export.'
  }
];

function listGameStageTemplates() {
  return GAME_STAGE_ARCHETYPES.map(t => Object.assign({}, t));
}

module.exports = {
  generateBlankSlateHtml,
  GAME_STAGE_ARCHETYPES,
  listGameStageTemplates,
  Generate_Blank_Slate_Html: generateBlankSlateHtml,
  List_Game_Stage_Templates: listGameStageTemplates
};

