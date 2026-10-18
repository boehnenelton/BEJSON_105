/**
 * Library:         app.js
 * Family:          static
 * Module Purpose:  Implements runtime functionality and logic for app.js.
 * Architecture:    BEJSON Core provides foundational format parsing, schema enforcement, path security, positional field map caching, and multi-format integration across runtime environments.
 * Version:         1.0.0
 * Release_Version: 300
 * Date:            2026-09-14
 * Author:          Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
 * Format_Creator:  Elton Boehnen
 * RELATIONAL_ID:   33e5f001-995d-4ee2-b28f-623ec798de2c
 */

/* ── Drawer ─────────────────────────────────────────────────────── */
function openDrawer() {
  var drawer  = document.getElementById('drawer');
  var overlay = document.getElementById('drawer-overlay');
  if (drawer)  drawer.classList.add('open');
  if (overlay) overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
  var drawer  = document.getElementById('drawer');
  var overlay = document.getElementById('drawer-overlay');
  if (drawer)  drawer.classList.remove('open');
  if (overlay) overlay.classList.remove('open');
  document.body.style.overflow = '';
}

/* Close drawer on Escape key */
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeDrawer();
});

/* ── Reparent row toggle ─────────────────────────────────────────── */
function toggleReparent(chunkId) {
  var row = document.getElementById('reparent-' + chunkId);
  if (!row) return;
  row.classList.toggle('open');
}

/* ── Flash auto-dismiss (5 seconds) ─────────────────────────────── */
(function() {
  var flashes = document.querySelectorAll('.flash');
  for (var i = 0; i < flashes.length; i++) {
    (function(el) {
      setTimeout(function() {
        if (el && el.parentElement) el.remove();
      }, 5000);
    })(flashes[i]);
  }
})();