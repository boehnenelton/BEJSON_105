/**
 * Library:        lib_bejson_Graphics_graphics_validator.js
 * Family:         Graphics
 * Description:    Graphics Domain VALIDATOR for JavaScript: Enforces two-tier barrier of entry
 *                 (Core Family Validator + Graphics Domain Validator) for blank-slate canvas stages,
 *                 timeline schemas, frame duration quantization, Remove_Frame_Source flags, and MFDB federation.
 * Version:        1.1.0
 * Date:           2026-11-01
 * Author:         Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  5a9b3c2d-0e4f-4a8b-9c2d-1f3a4b5c6d7e
 * Release_Version: 300
 */

'use strict';

const fs = require('fs');
const path = require('path');

// Sibling family resolution
const coreValidatorPath = path.resolve(__dirname, '../Core/lib_bejson_Core_bejson_validator.js');
const coreValidator = require(coreValidatorPath);
const schemas = require('./lib_bejson_Graphics_graphics_schemas');

const VALID_GRAPHICS_RECORDS_TYPES = new Set([
  'GraphicCanvasConfig',
  'GraphicFrameRecord',
  'GraphicTimelineRecord',
  'SvgAnimationTimelineRecord',
  'GraphicCanvasTemplate',
  'CanvasTemplateRecord',
  'GraphicStageRecord',
  'GraphicTextureTile',
  'GraphicSlideshowRecord',
  'GraphicSlideRecord',
  'BrandingSlideRecord',
  'mfdb'
]);

const AUTHORIZED_PALETTE_HEX = new Set([
  '#000000', '#FFFFFF', '#DE2626',
  '#08080C', '#0C0C10', '#14141A', '#14141E', '#1C1C24', '#2A2A38', '#333333'
]);

const ASPECT_RATIO_RE = /^\d+:\d+$/;

function checkPalette(colorStr) {
  if (typeof colorStr !== 'string') return false;
  const upper = colorStr.trim().toUpperCase();
  if (AUTHORIZED_PALETTE_HEX.has(upper)) return true;
  if (upper.startsWith('RGBA(') || upper.startsWith('RGB(')) return true;
  return false;
}

function checkSvg(svgMarkup) {
  if (typeof svgMarkup !== 'string') return { valid: false, error: 'SVG markup is not a string' };
  const stripped = svgMarkup.trim();
  if (!stripped) return { valid: false, error: 'SVG markup is empty' };
  if (stripped.endsWith('.svg') || stripped.endsWith('.SVG')) return { valid: true };
  if (!stripped.startsWith('<svg') || !stripped.includes('</svg>')) {
    return { valid: false, error: 'SVG markup does not contain valid <svg> and </svg> tags or valid .svg filename' };
  }
  return { valid: true };
}

function validateGraphicsBarrier(inputData, isFile = false) {
  // -------------------------------------------------------------------------
  // Barrier 1: Foundational Core Family Barrier
  // -------------------------------------------------------------------------
  const coreResult = coreValidator.validate_bejson(inputData, isFile);
  const errors = Array.isArray(coreResult.errors) ? [...coreResult.errors] : [];
  const warnings = Array.isArray(coreResult.warnings) ? [...coreResult.warnings] : [];

  if (!coreResult.valid) {
    errors.unshift(`[E_GRAPHICS_CORE_VALIDATION_FAILED] Core Family barrier rejected document (${errors.length} core errors)`);
    return { valid: false, errors, warnings, current_file: coreResult.current_file || '' };
  }

  // Load document object
  let doc = null;
  if (isFile) {
    try {
      const content = fs.readFileSync(path.resolve(inputData), 'utf8');
      doc = JSON.parse(content);
    } catch (err) {
      errors.push(`Failed to read file for graphics validation: ${err.message}`);
      return { valid: false, errors, warnings, current_file: String(inputData) };
    }
  } else if (typeof inputData === 'string') {
    try {
      doc = JSON.parse(inputData);
    } catch (err) {
      errors.push(`Failed to parse JSON string: ${err.message}`);
      return { valid: false, errors, warnings, current_file: '' };
    }
  } else if (typeof inputData === 'object' && inputData !== null) {
    doc = inputData;
  }

  // -------------------------------------------------------------------------
  // Barrier 2: Graphics Domain Barrier
  // -------------------------------------------------------------------------
  if (Array.isArray(doc.Records_Type)) {
    for (const rType of doc.Records_Type) {
      if (!VALID_GRAPHICS_RECORDS_TYPES.has(rType)) {
        warnings.push(`[E_GRAPHICS_INVALID_RECORDS_TYPE] Unregistered Graphics Records_Type '${rType}'`);
      }
    }
  }

  // 2.1 Check Top-Level Remove_Frame_Source boolean header
  if ('Remove_Frame_Source' in doc) {
    if (typeof doc.Remove_Frame_Source !== 'boolean') {
      errors.push(`[E_GRAPHICS_STAGE_CONFIG_INVALID] Header 'Remove_Frame_Source' must be a boolean, got ${typeof doc.Remove_Frame_Source}`);
    }
  }

  // 2.2 Check Dimensions in Header
  if (doc.Width_Px !== undefined) {
    if (!Number.isInteger(doc.Width_Px) || doc.Width_Px <= 0) {
      errors.push(`[E_GRAPHICS_INVALID_DIMENSIONS] Width_Px must be an integer > 0, got ${doc.Width_Px}`);
    }
  }
  if (doc.Height_Px !== undefined) {
    if (!Number.isInteger(doc.Height_Px) || doc.Height_Px <= 0) {
      errors.push(`[E_GRAPHICS_INVALID_DIMENSIONS] Height_Px must be an integer > 0, got ${doc.Height_Px}`);
    }
  }

  // 2.3 Check Aspect Ratio
  if (doc.Aspect_Ratio !== undefined) {
    if (typeof doc.Aspect_Ratio !== 'string' || !ASPECT_RATIO_RE.test(doc.Aspect_Ratio)) {
      errors.push(`[E_GRAPHICS_INVALID_ASPECT_RATIO] Aspect_Ratio '${doc.Aspect_Ratio}' must match format 'W:H'`);
    }
  }

  // 2.4 Check FPS in Header
  if (doc.FPS !== undefined) {
    if (!Number.isInteger(doc.FPS) || doc.FPS <= 0) {
      errors.push(`[E_GRAPHICS_INVALID_FPS] FPS must be an integer > 0, got ${doc.FPS}`);
    }
  }

  // 2.5 Check Duration in Header
  if (doc.Duration_Sec !== undefined) {
    if (typeof doc.Duration_Sec !== 'number' || doc.Duration_Sec <= 0) {
      errors.push(`[E_GRAPHICS_INVALID_DURATION] Duration_Sec must be a number > 0, got ${doc.Duration_Sec}`);
    }
  }
  if (doc.Total_Duration_Ms !== undefined) {
    if (typeof doc.Total_Duration_Ms !== 'number' || doc.Total_Duration_Ms <= 0) {
      errors.push(`[E_GRAPHICS_INVALID_DURATION] Total_Duration_Ms must be a number > 0, got ${doc.Total_Duration_Ms}`);
    }
  }

  // 2.6 Row-Level Checks via Field Map
  const valuesRows = doc.Values || [];
  if (Array.isArray(valuesRows) && valuesRows.length > 0 && Array.isArray(doc.Fields)) {
    const fieldMap = schemas.buildFieldMap105(doc.Fields);

    let lastFrameIdx = -1;
    valuesRows.forEach((row, rowIdx) => {
      if (!Array.isArray(row)) return;

      // Sequential frame_index
      if ('frame_index' in fieldMap) {
        const col = fieldMap.frame_index;
        if (col < row.length) {
          const fIdx = row[col];
          if (!Number.isInteger(fIdx) || fIdx < 0) {
            errors.push(`[E_GRAPHICS_INVALID_FRAME_SEQUENCE] Row #${rowIdx} frame_index must be non-negative integer`);
          } else if (fIdx !== lastFrameIdx + 1) {
            errors.push(`[E_GRAPHICS_INVALID_FRAME_SEQUENCE] Row #${rowIdx} non-sequential frame_index ${fIdx}; expected ${lastFrameIdx + 1}`);
          }
          lastFrameIdx = fIdx;
        }
      }

      // frame_duration_ms > 0
      if ('frame_duration_ms' in fieldMap) {
        const col = fieldMap.frame_duration_ms;
        if (col < row.length) {
          const dur = row[col];
          if (typeof dur !== 'number' || dur <= 0) {
            errors.push(`[E_GRAPHICS_INVALID_DURATION] Row #${rowIdx} frame_duration_ms must be > 0`);
          }
        }
      }

      // seek_progress in range [0, 100]
      if ('seek_progress' in fieldMap) {
        const col = fieldMap.seek_progress;
        if (col < row.length) {
          const seek = row[col];
          if (typeof seek !== 'number' || seek < 0 || seek > 100) {
            errors.push(`[E_GRAPHICS_INVALID_TIMELINE_ROW] Row #${rowIdx} seek_progress out of bounds`);
          }
        }
      }

      // svg_markup validity
      if ('svg_markup' in fieldMap) {
        const col = fieldMap.svg_markup;
        if (col < row.length) {
          const svgContent = row[col];
          if (svgContent) {
            const svgCheck = checkSvg(svgContent);
            if (!svgCheck.valid) {
              errors.push(`[E_GRAPHICS_INVALID_SVG_MARKUP] Row #${rowIdx} ${svgCheck.error}`);
            }
          }
        }
      }

      // remove_frame_source in row
      if ('remove_frame_source' in fieldMap) {
        const col = fieldMap.remove_frame_source;
        if (col < row.length) {
          const rfs = row[col];
          if (typeof rfs !== 'boolean') {
            errors.push(`[E_GRAPHICS_STAGE_CONFIG_INVALID] Row #${rowIdx} remove_frame_source must be a boolean`);
          }
        }
      }

      // Palette checks
      if ('accent_color' in fieldMap) {
        const col = fieldMap.accent_color;
        if (col < row.length && row[col] && !checkPalette(row[col])) {
          warnings.push(`[E_GRAPHICS_PALETTE_VIOLATION] Row #${rowIdx} accent_color '${row[col]}' deviates from Policy §8.1 Tri-Color Palette`);
        }
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    current_file: isFile ? String(inputData) : ''
  };
}

module.exports = {
  VALID_GRAPHICS_RECORDS_TYPES,
  AUTHORIZED_PALETTE_HEX,
  checkPalette,
  checkSvg,
  validateGraphicsBarrier
};
