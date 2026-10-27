/**
 * Library:        lib_bejson_Canvas_canvas_templates.js
 * Family:         Canvas
 * Description:    Fixed-Size Canvas and Seamless Texture Tile Template Manager for
 *                 SVG Animations and Deterministic Playwright Screenshot Captures.
 * BEJSON:         BEJSON stands for BOEHNEN ELTON JSON. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * MFDB:           MFDB stands for Multi File Database. Authoritative definition;
 *                 do not restate or reinterpret this acronym elsewhere.
 * Version:        1.0.0
 * Date:           2026-10-25
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * RELATIONAL_ID:  2c3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f
 * Release_Version: 300
 */

'use strict';

const fs = (typeof require !== 'undefined') ? require('fs') : null;
const path = (typeof require !== 'undefined') ? require('path') : null;

const CANVAS_TEMPLATE_CATALOG = {
  'template_square_800x800.html': {
    name: 'template_square_800x800.html',
    category: 'fixed_stage',
    width_px: 800,
    height_px: 800,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'Isometric 3D cube matrix, rotating reticle rings, telemetry HUD',
    default_duration_sec: 8.0,
    bg_theme: '#000000'
  },
  'template_banner_840x420.html': {
    name: 'template_banner_840x420.html',
    category: 'fixed_stage',
    width_px: 840,
    height_px: 420,
    aspect_ratio: '2:1',
    selector: '#capture-stage',
    motif: '8-lane production grid, scanning data waves, 420p downscale target',
    default_duration_sec: 6.0,
    bg_theme: '#000000'
  },
  'template_widescreen_1280x720.html': {
    name: 'template_widescreen_1280x720.html',
    category: 'fixed_stage',
    width_px: 1280,
    height_px: 720,
    aspect_ratio: '16:9',
    selector: '#capture-stage',
    motif: '6-Tier Layered Architecture visual matrix, bus lines, pulse nodes',
    default_duration_sec: 10.0,
    bg_theme: '#000000'
  },
  'template_portrait_720x1280.html': {
    name: 'template_portrait_720x1280.html',
    category: 'fixed_stage',
    width_px: 720,
    height_px: 1280,
    aspect_ratio: '9:16',
    selector: '#capture-stage',
    motif: 'Vertical telemetry rail, waterfall stream, stacked layer status cards',
    default_duration_sec: 8.0,
    bg_theme: '#000000'
  },
  'template_universal_stage.html': {
    name: 'template_universal_stage.html',
    category: 'dynamic_stage',
    width_px: 800,
    height_px: 800,
    aspect_ratio: 'dynamic',
    selector: '#capture-stage',
    motif: 'Parameterized dynamic stage with query parameter controls (?size=, ?bg=, ?svg=)',
    default_duration_sec: 8.0,
    bg_theme: '#000000'
  },
  'template_texture_isometric_cube.html': {
    name: 'template_texture_isometric_cube.html',
    category: 'seamless_tile',
    width_px: 800,
    height_px: 800,
    tile_unit_size: 128,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    unit_selector: '#tile-unit svg',
    motif: '104a Isometric cube complex with floating top and pulsing vertices',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_texture_checkerboard.html': {
    name: 'template_texture_checkerboard.html',
    category: 'seamless_tile',
    width_px: 840,
    height_px: 420,
    tile_unit_size: 64,
    aspect_ratio: '2:1',
    selector: '#capture-stage',
    unit_selector: '#tile-unit svg',
    motif: 'Dual-tone checkerboard with micro-crosshairs and pulsing red reticles',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_texture_circuit_grid.html': {
    name: 'template_texture_circuit_grid.html',
    category: 'seamless_tile',
    width_px: 1280,
    height_px: 720,
    tile_unit_size: 64,
    aspect_ratio: '16:9',
    selector: '#capture-stage',
    unit_selector: '#tile-unit svg',
    motif: 'Continuous electronic PCB bus traces with pulsing transmission tracks',
    default_duration_sec: 6.0,
    bg_theme: '#000000'
  },
  'template_texture_tile_studio.html': {
    name: 'template_texture_tile_studio.html',
    category: 'interactive_studio',
    width_px: 840,
    height_px: 420,
    tile_unit_size: 128,
    aspect_ratio: 'multi',
    selector: '#capture-stage',
    unit_selector: '#tile-unit svg',
    motif: 'Master interactive studio: Cube, Checkerboard, Circuit, Hex Mesh, Dots',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_icon_512x512.html': {
    name: 'template_icon_512x512.html',
    category: 'icon_stage',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '512px Master App Icon / PWA splash icon, floating 104a cube and reticle rings',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_icon_256x256.html': {
    name: 'template_icon_256x256.html',
    category: 'icon_stage',
    width_px: 256,
    height_px: 256,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '256px Application launcher icon, hexagonal aperture and glowing cube nucleus',
    default_duration_sec: 3.5,
    bg_theme: '#000000'
  },
  'template_icon_128x128.html': {
    name: 'template_icon_128x128.html',
    category: 'icon_stage',
    width_px: 128,
    height_px: 128,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '128px System icon / widget badge, high-contrast isometric cube glyph',
    default_duration_sec: 3.0,
    bg_theme: '#000000'
  },
  'template_icon_64x64.html': {
    name: 'template_icon_64x64.html',
    category: 'icon_stage',
    width_px: 64,
    height_px: 64,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '64px Toolbar / navigation micro-icon, pixel-snapped cube silhouette',
    default_duration_sec: 2.0,
    bg_theme: '#000000'
  },
  'template_icon_32x32.html': {
    name: 'template_icon_32x32.html',
    category: 'icon_stage',
    width_px: 32,
    height_px: 32,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '32px Favicon / terminal prompt glyph, micro isometric cube and red pip',
    default_duration_sec: 1.8,
    bg_theme: '#000000'
  },
  'template_graphic_badge_400x200.html': {
    name: 'template_graphic_badge_400x200.html',
    category: 'small_graphic',
    width_px: 400,
    height_px: 200,
    aspect_ratio: '2:1',
    selector: '#capture-stage',
    motif: '400x200 Component badge, chamfered frame, scanline sweep and telemetry readout',
    default_duration_sec: 3.0,
    bg_theme: '#000000'
  },
  'template_graphic_kpi_card_320x320.html': {
    name: 'template_graphic_kpi_card_320x320.html',
    category: 'small_graphic',
    width_px: 320,
    height_px: 320,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: '320x320 Compact KPI metric card, radial dial gauge with red indicator arc',
    default_duration_sec: 3.0,
    bg_theme: '#000000'
  },
  'template_graphic_button_240x80.html': {
    name: 'template_graphic_button_240x80.html',
    category: 'small_graphic',
    width_px: 240,
    height_px: 80,
    aspect_ratio: '3:1',
    selector: '#capture-stage',
    motif: '240x80 Cyber action button / control pill, glowing perimeter and micro-cube',
    default_duration_sec: 2.5,
    bg_theme: '#000000'
  },
  'template_graphic_chip_160x48.html': {
    name: 'template_graphic_chip_160x48.html',
    category: 'small_graphic',
    width_px: 160,
    height_px: 48,
    aspect_ratio: '10:3',
    selector: '#capture-stage',
    motif: '160x48 Micro chip tag / tier badge, pulsing status pip and circuit trace',
    default_duration_sec: 2.0,
    bg_theme: '#000000'
  },
  'template_icon_studio.html': {
    name: 'template_icon_studio.html',
    category: 'dynamic_studio',
    width_px: 256,
    height_px: 256,
    aspect_ratio: 'dynamic',
    selector: '#capture-stage',
    motif: 'Dynamic Icon & Graphic Studio with URL query controls (?size=, ?bg=)',
    default_duration_sec: 3.0,
    bg_theme: '#000000'
  },
  'template_icon_bejson_104_standard.html': {
    name: 'template_icon_bejson_104_standard.html',
    category: 'bejson_cube_icon',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'BEJSON 104 Standard Monolith Cube: solid isometric cube, pulsing vertices, telemetry ring',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_icon_bejson_104a_floating.html': {
    name: 'template_icon_bejson_104a_floating.html',
    category: 'bejson_cube_icon',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'BEJSON 104a Floating Cap Cube: signature levitating floating diamond top, plasma energy beams',
    default_duration_sec: 3.5,
    bg_theme: '#000000'
  },
  'template_icon_bejson_104db_pillar.html': {
    name: 'template_icon_bejson_104db_pillar.html',
    category: 'bejson_cube_icon',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'BEJSON 104db Stacked Pillar: vertical monolithic pillar of 3 cubes with cascading red data pulses',
    default_duration_sec: 3.0,
    bg_theme: '#000000'
  },
  'template_icon_bejson_104_nested.html': {
    name: 'template_icon_bejson_104_nested.html',
    category: 'bejson_cube_icon',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'BEJSON Nested Cube: wireframe outer container cube with spinning inner luminous child cube',
    default_duration_sec: 4.0,
    bg_theme: '#000000'
  },
  'template_icon_bejson_mfdb_federation.html': {
    name: 'template_icon_bejson_mfdb_federation.html',
    category: 'bejson_cube_icon',
    width_px: 512,
    height_px: 512,
    aspect_ratio: '1:1',
    selector: '#capture-stage',
    motif: 'BEJSON MFDB Federated Network: large central master cube transmitting to 4 orbiting slave cubes',
    default_duration_sec: 3.5,
    bg_theme: '#000000'
  }
};

const TEMPLATE_ROOT_CANDIDATES = [
  '/storage/emulated/0/Admin/Dev/Templates/Canvas_SVG_Capture_Templates',
  '/storage/emulated/0/Admin/Dev/Skills/agy-consolidated/playwright-termux-automation/assets/canvas_templates'
];

function resolveTemplateRoot() {
  if (fs) {
    for (const cand of TEMPLATE_ROOT_CANDIDATES) {
      if (fs.existsSync(cand) && fs.statSync(cand).isDirectory()) {
        return cand;
      }
    }
  }
  return TEMPLATE_ROOT_CANDIDATES[0];
}

function listCanvasTemplates() {
  const root = resolveTemplateRoot();
  const catalogList = [];
  for (const [name, meta] of Object.entries(CANVAS_TEMPLATE_CATALOG)) {
    const entry = Object.assign({}, meta);
    if (fs && path) {
      const fullPath = path.join(root, name);
      entry.exists_on_disk = fs.existsSync(fullPath);
      entry.disk_path = entry.exists_on_disk ? fullPath : null;
    }
    catalogList.push(entry);
  }
  return catalogList;
}

function getTemplatePath(templateName) {
  if (!templateName.endsWith('.html')) {
    templateName += '.html';
  }
  if (fs && path) {
    for (const cand of TEMPLATE_ROOT_CANDIDATES) {
      const p = path.join(cand, templateName);
      if (fs.existsSync(p)) return p;
    }
    return path.join(resolveTemplateRoot(), templateName);
  }
  return `${TEMPLATE_ROOT_CANDIDATES[0]}/${templateName}`;
}

function loadTemplate(templateName) {
  if (!fs) throw new Error('fs module unavailable');
  const targetPath = getTemplatePath(templateName);
  return fs.readFileSync(targetPath, 'utf8');
}

function renderCanvasHtml(templateName, options = {}) {
  let html = loadTemplate(templateName);

  if (options.custom_svg_markup) {
    const containerRegex = /(<div class="svg-container">)([\s\S]*?)(<\/div>)/;
    if (containerRegex.test(html)) {
      html = html.replace(containerRegex, `$1\n${options.custom_svg_markup}\n$3`);
    } else {
      const tileRegex = /(<div id="tile-unit"[^>]*>)([\s\S]*?)(<\/div>)/;
      if (tileRegex.test(html)) {
        html = html.replace(tileRegex, `$1\n${options.custom_svg_markup}\n$3`);
      }
    }
  }

  if (options.width_px) {
    html = html.replace(/width:\s*\d+px;/, `width: ${options.width_px}px;`);
  }
  if (options.height_px) {
    html = html.replace(/height:\s*\d+px;/, `height: ${options.height_px}px;`);
  }
  if (options.duration_sec && options.duration_sec > 0) {
    html = html.replace(/const totalDurationSec\s*=\s*[\d\.]+;/, `const totalDurationSec = ${options.duration_sec};`);
  }
  if (options.accent_color) {
    html = html.split('#DE2626').join(options.accent_color);
  }

  return html;
}

const moduleExports = {
  CANVAS_TEMPLATE_CATALOG,
  resolveTemplateRoot,
  listCanvasTemplates,
  getTemplatePath,
  loadTemplate,
  renderCanvasHtml
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = moduleExports;
}
if (typeof window !== 'undefined') {
  window.lib_bejson_Canvas_canvas_templates = moduleExports;
}
