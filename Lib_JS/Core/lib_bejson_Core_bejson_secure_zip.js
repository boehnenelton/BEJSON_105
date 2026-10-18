/**
 * Library:         lib_bejson_Core_bejson_secure_zip.js
 * Family:          Core
 * Module Purpose:  Zip-entry path normalization and validation that blocks root-escaping paths (secure_zip_validate).
 * Architecture:    Runtime or environment helper. It defines no BEJSON format rules.
 * Format_Scope:    None (not a format module)
 * Glossary:        BEJSON 104, 104a and 104db are the three file formats (Format_Version). 104db = ONE file holding 2+ entity types
 *                  (Record_Type_Parent discriminator, null-padding). MFDB is NOT a format and NOT 104db: it is a layer made of one 104a manifest
 *                  (104a.mfdb.bejson) plus dense 104 entity files linked by Parent_Hierarchy. MFDB-132 = an MFDB packed into one Chunked-104a document.
 * Version:         1.1.4
 * Release_Version: 300
 * Date:            2026-10-02
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   ccd1d678-119a-4f91-aed3-acd108894e90
 */

'use strict';

const _nodePath = (typeof require !== 'undefined') ? (() => { try { return require('path'); } catch { return null; } })() : null;

/**
 * Normalizes a zip-entry path (slashes, '.' and '..' segments) so it can be compared with the target directory.
 */
/**
 * Pure-JS POSIX path normalizer — stack-based, zero Node.js dependency.
 * Resolves `.` and `..` segments. Never produces a path that escapes root.
 * @param {string} rawPath
 * @returns {string} normalized path (always starts with "/")
 */
function _normalizePath(rawPath) {
    const parts = rawPath.replace(/\\/g, '/').split('/');
    const stack = [];
    for (const part of parts) {
        if (part === '' || part === '.') continue;
        if (part === '..') { if (stack.length > 0) stack.pop(); }
        else stack.push(part);
    }
    return '/' + stack.join('/');
}

/**
 * Checks every entry of a zip against targetDir and rejects any that would extract outside it (Zip Slip). Generic zip safety; no BEJSON format rules.
 */
/**
 * Validates entries in a ZIP archive to ensure they do not escape the target directory.
 * Works in Node.js, Android WebView, and all browser environments.
 * @param {object} zip - adm-zip or compatible object with getEntries()
 * @param {string} targetDir - The base directory for extraction
 * @throws {Error} if Zip Slip is detected or a dangerous key name is found
 */
function secure_zip_validate(zip, targetDir) {
    // Normalize target dir — use Node path when available, pure-JS otherwise
    const normalizeAbs = _nodePath
        ? (p) => _nodePath.resolve(p)
        : (p) => _normalizePath(p);

    const targetPath = normalizeAbs(targetDir);
    const sep = _nodePath ? _nodePath.sep : '/';
    // Ensure targetPath always ends with separator so startsWith check is prefix-exact
    const targetWithSep = targetPath.endsWith(sep) ? targetPath : targetPath + sep;

    zip.getEntries().forEach(entry => {
        const entryName = entry.entryName;

        // Block prototype pollution keys embedded in archive entry names
        const parts = entryName.replace(/\\/g, '/').split('/');
        for (const part of parts) {
            if (part === '__proto__' || part === 'constructor' || part === 'prototype') {
                throw new Error(`Zip Slip (proto key): "${entryName}" contains a forbidden path segment`);
            }
        }

        // Resolve full target path
        const entryPath = _nodePath
            ? _nodePath.resolve(targetPath, entryName)
            : _normalizePath(targetPath + '/' + entryName);

        const entryWithSep = entryPath.endsWith(sep) ? entryPath : entryPath + sep;

        if (!entryPath.startsWith(targetPath + sep) && entryPath !== targetPath) {
            throw new Error(`Zip Slip detected: "${entryName}" attempts to escape target directory`);
        }
    });
    return true;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { secure_zip_validate };
}
if (typeof window !== 'undefined') {
    window.BEJSON_UTILITY = window.BEJSON_UTILITY || {};
    window.BEJSON_UTILITY.secure_zip_validate = secure_zip_validate;
}