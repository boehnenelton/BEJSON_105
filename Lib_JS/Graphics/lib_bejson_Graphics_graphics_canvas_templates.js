/**
 * Library:        lib_bejson_Graphics_graphics_canvas_templates.js
 * Family:         Graphics
 * Description:    Blank-Slate Canvas Stage Templates in JavaScript for BEJSON 105a.
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Version:        1.0.0
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

module.exports = {
  generateBlankSlateHtml
};
