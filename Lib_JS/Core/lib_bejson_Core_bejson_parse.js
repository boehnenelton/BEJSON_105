/**
 * Library:        lib_bejson_Core_bejson_parse.js
 * Family:         Core
 * Description:    Rapid indexing and retrieval engine for dense tabular data.
 * Version:        2.0.5
 * Date:           2026-10-03
 * Author:         Elton Boehnen
 * Contact:        eltonboehnen@gmail.com | boehnenelton2024.pages.dev | github.com/boehnenelton
 * Format_Creator: Elton Boehnen
 * RELATIONAL_ID:  455ff0ca-ed56-4381-a7bd-f794a4cf2ea2
 * Release_Version: 300
 *
 * Changelog:
 *   2.0.4 - Audit fix (2026-08-15 second-pass audit, HIGH-4): parse_json()
 *           always regex-extracted a { ... } span BEFORE attempting
 *           JSON.parse, even for already-clean input -- the extraction
 *           regex is greedy (first { to LAST }) and unbounded, so
 *           multi-object or pathological input could over-capture or cost
 *           real backtracking time. Now tries JSON.parse(text) directly
 *           first (the common case never touches the regex at all), only
 *           falls back to regex extraction on failure, and caps the
 *           fallback input at 500,000 chars. Side benefit found during
 *           testing: the previously-silent multi-object over-capture case
 *           now throws a clean parse error instead of returning malformed
 *           data, since the captured span is no longer trusted without
 *           re-validating through JSON.parse.
 */

'use strict';

// ------------------------------------------------------------------
// BEJSON ecosystem — core + validator sourced here
// ------------------------------------------------------------------
const {
  BEJSONCoreError,
  bejson_core_is_valid,
  bejson_core_warm,
  bejson_core_get_version,
  bejson_core_get_stats,
} = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_core.js') : (window.BEJSON || {});

const {
  BEJSONValidationError,
  bejson_validator_validate_string,
  bejson_validator_get_report,
} = (typeof require !== 'undefined') ? require('./lib_bejson_Core_bejson_validator.js') : (window.BEJSON_VALIDATOR || {});

// ------------------------------------------------------------------
// PARSER CORE  — methods mirrored verbatim from the Python lib
// ------------------------------------------------------------------

/**
 * Optimal BEJSON Parsing Standard (JS/TS)
 * Step 1: Pre-process to strip wrappers (Markdown, HTML, Prose)
 * Step 2: Use native JSON.parse()
 * Step 3: (Caller Mandate) Pass to structural validator
 */
function parse_json(text) {
  if (typeof text !== 'string') return text;

  let doc;
  try {
    // 1. Fast path: try native JSON.parse on the raw text first. Most
    //    callers pass already-clean JSON, so this avoids the regex
    //    extraction below entirely for the common case.
    doc = JSON.parse(text);
  } catch (e1) {
    // 2. Fallback: text wasn't clean JSON on its own (markdown fences,
    //    prose wrapper, etc). Extract the { ... } span and try again.
    //    HIGH-4 audit fix (2026-08-15): this regex is greedy and matches
    //    from the FIRST { to the LAST } in the input -- if the input has
    //    multiple JSON objects or trailing prose containing '}', it will
    //    over-capture. It's also unbounded, so pathological input (many
    //    nested/unmatched braces) could cost real backtracking time. The
    //    length cap below bounds the worst case; the fast path above
    //    means well-formed input never touches this regex at all.
    const MAX_EXTRACT_LEN = 500_000;
    const capped = text.length > MAX_EXTRACT_LEN ? text.slice(0, MAX_EXTRACT_LEN) : text;
    const match = capped.match(/\{[\s\S]*\}/);
    if (!match) {
      throw new Error('BEJSON Parse Failure: ' + e1.message);
    }
    try {
      doc = JSON.parse(match[0]);
    } catch (e2) {
      throw new Error('BEJSON Parse Failure: ' + e2.message);
    }
  }

  // 3. Structural Validation Enforcement
  if (typeof bejson_core_is_valid === 'function') {
      if (!bejson_core_is_valid(doc)) {
          console.error('[BEJSON] Parsing complete but validation failed.');
      }
  }

  // 4. Born warm: 105-series docs get their field map built here so no
  //    caller ever has to (104-series untouched, lazy).
  return (typeof bejson_core_warm === 'function') ? bejson_core_warm(doc) : doc;
}

function extract_data(data) {
  const fields = data.Fields || [];
  const values = data.Values || [];
  if (!values.length) return ['My_Project', []];

  const fMap = {};
  fields.forEach((f, i) => {
    const key = f.name.toLowerCase().replace(/[^a-z0-9]/g, '');
    fMap[key] = i;
  });

  function getVal(row, key) {
    const idx = fMap[key];
    if (idx !== undefined && idx < row.length) {
      const v = row[idx];
      if (v !== null && v !== undefined) return String(v).trim();
    }
    return null;
  }

  let projectName = 'My_Project';
  for (const row of values) {
    for (const key of ['projectname', 'zipfilename', 'containername']) {
      const v = getVal(row, key);
      if (v) { projectName = v; break; }
    }
    if (projectName !== 'My_Project') break;
  }

  projectName = projectName.replace(/[<>:"/\\|?*]/g, '_');

  const files = [];
  for (const row of values) {
    for (let i = 1; i <= 50; i++) {
      const fname = getVal(row, 'file' + i + 'name');
      const fcont = getVal(row, 'file' + i + 'content');
      if (fname && fcont) files.push({ name: fname, content: fcont });
    }
  }

  return [projectName, files];
}

function save_files(proj, files, cfg) {
  if (typeof require === 'undefined') {
    return { success: false, message: 'save_files is only available in Node.js environments' };
  }
  
  const fs      = require('fs');
  const path    = require('path');
  let AdmZip;
  try { AdmZip = require('adm-zip'); } catch (e) { /* optional dependency */ }
  
  const { secure_zip_validate } = require('./lib_bejson_Core_bejson_secure_zip.js');

  const scriptDir  = path.dirname(path.resolve(__filename || __dirname));
  const DEFAULT_OUT = path.join(scriptDir, 'output');

  const baseDir   = (cfg.output_path || DEFAULT_OUT).trim() || DEFAULT_OUT;
  const overwrite = !!cfg.overwrite_enabled;

  if (!fs.existsSync(baseDir)) {
    try { fs.mkdirSync(baseDir, { recursive: true }); }
    catch (e) { return { success: false, message: 'Cannot create output dir: ' + e.message }; }
  }

  let target;
  if (overwrite) {
    target = path.join(baseDir, proj);
    const bakTarget = path.join(baseDir, proj + '_BACKUP');
    if (fs.existsSync(target)) {
      if (fs.existsSync(bakTarget)) _rmrf(bakTarget);
      try { _cpdirSync(target, bakTarget); }
      catch (e) { console.warn('Backup warning: ' + e.message); }
    }
  } else {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    const ts  = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}` +
                `_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    target = path.join(baseDir, ts + '_' + proj);
  }

  try {
    // Phase 2: Resolve and Guard target path
    const targetPath = path.resolve(target);
    fs.mkdirSync(targetPath, { recursive: true });

    for (const f of files) {
      // Phase 2: Assert boundary prefixes (mitigate Zip Slip / Traversal)
      const fpath = path.resolve(targetPath, f.name);
      if (!fpath.startsWith(targetPath)) {
        throw new Error(`Path Traversal detected: "${f.name}" escapes target directory`);
      }
      
      const fdir  = path.dirname(fpath);
      if (!fs.existsSync(fdir)) fs.mkdirSync(fdir, { recursive: true });
      fs.writeFileSync(fpath, f.content, 'utf8');
    }

    // Build report
    const now     = new Date();
    const tsNow   = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-` +
                    `${String(now.getDate()).padStart(2,'0')} ` +
                    `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:` +
                    `${String(now.getSeconds()).padStart(2,'0')}`;
    const modeStr = overwrite ? 'Merge/Update (overwrite)' : 'Timestamped (new folder)';
    const sep52   = '='.repeat(52);
    const dash52  = '-'.repeat(52);

    const lines = [
      sep52,
      '  STRUCTURED PARSER — BUILD REPORT',
      sep52,
      'Project    : ' + proj,
      'Generated  : ' + tsNow,
      'Mode       : ' + modeStr,
      'Output Dir : ' + target,
      'Files      : ' + files.length,
      dash52,
      'FILE LIST',
      dash52,
    ];

    files.forEach((f, idx) => {
      const sizeB = Buffer.byteLength(f.content, 'utf8');
      const sizeS = sizeB >= 1024 ? (sizeB / 1024).toFixed(1) + ' KB' : sizeB + ' B';
      lines.push('  [' + String(idx + 1).padStart(2, '0') + '] ' + f.name + '  (' + sizeS + ')');
    });

    lines.push(dash52);
    lines.push('Zip        : ' + proj + '_update.zip');
    lines.push(sep52);
    const reportText = lines.join('\n') + '\n';

    // Write report to disk
    fs.writeFileSync(path.join(target, '_REPORT.txt'), reportText, 'utf8');

    // Build zip (files + report)
    // guard against adm-zip not being installed. Without this guard,
    // new AdmZip() throws TypeError after files have already been written to disk.
    if (!AdmZip) {
      return { success: false, message: 'adm-zip is not installed. Run: npm install adm-zip' };
    }
    const zip = new AdmZip();
    for (const f of files) zip.addFile(f.name, Buffer.from(f.content, 'utf8'));
    zip.addFile('_REPORT.txt', Buffer.from(reportText, 'utf8'));
    zip.writeZip(path.join(target, proj + '_update.zip'));

    return {
      success:    true,
      message:    'Saved ' + files.length + ' file(s)',
      path:       target,
      file_count: files.length,
    };

  } catch (e) {
    return { success: false, message: e.message };
  }
}

// ------------------------------------------------------------------
// Internal helpers
// ------------------------------------------------------------------

function _rmrf(dir) {
  const fs   = require('fs');
  const path = require('path');
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (fs.lstatSync(full).isDirectory()) _rmrf(full);
    else fs.unlinkSync(full);
  }
  fs.rmdirSync(dir);
}

function _cpdirSync(src, dest) {
  const fs   = require('fs');
  const path = require('path');
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src)) {
    const srcPath  = path.join(src,  entry);
    const destPath = path.join(dest, entry);
    if (fs.lstatSync(srcPath).isDirectory()) _cpdirSync(srcPath, destPath);
    else fs.copyFileSync(srcPath, destPath);
  }
}

// ------------------------------------------------------------------
// Exports
// ------------------------------------------------------------------

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    parse_json,
    extract_data,
    save_files,
  };
}
