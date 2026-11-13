"""
step21_sidebar_redesign.py
==========================
OrbisERP Sidebar Redesign – Remove the Dock (first column).

GOAL
----
The current layout shows two visual columns:
  1. A narrow dock (#desk-dock) listing icons for every ERP module
     (the "first column" the user wants removed).
  2. The main sidebar (.body-sidebar) showing the active module's
     icon + name in the header and navigation links below.

We want ONE column only – the sidebar – whose header already shows
the active module's icon and name when the dock is absent.

APPROACH  (zero core-file edits)
---------
Two files are created / updated:

A. /sites/frontend/public/files/orbis_sidebar_redesign.js
   • JS that patches frappe.ui.Sidebar.dock_enabled() → false,
     neutralises frappe.ui.Dock.refresh(), and hides any dock DOM.
   • CSS injected into <head> that hides #desk-dock / .dock,
     fixes any leftover spacing, and ensures the sidebar header
     logo is always visible.

B. /sites/frontend/site_config.json
   • app_include_js key is extended to reference the JS file above.
     Frappe's desk.py reads frappe.conf.app_include_js and adds it
     to the <script> tags in desk.html.  No core edit required.

Switching modules, permissions, search, notifications, sidebar
collapse/expand, and responsive behaviour are all preserved because
the underlying frappe.ui.Sidebar logic is untouched – only the
dock layer is disabled.
"""

import json
import os
import frappe


# ─── JS (+ inline CSS) placed in site public/files ───────────────────────────

ORBIS_JS = r"""
/* =============================================================
   OrbisERP Sidebar Redesign v1
   Removes the dock (left module-icon column) so that only the
   contextual sidebar remains.

   Supported customisation surface:
     • frappe.conf.app_include_js  (site_config.json)
   No ERPNext / Frappe core files are modified.
   ============================================================= */

// ── 1. CSS – injected immediately so the dock never flashes ──────────────────
(function injectOrbisCSS() {
    var id = "orbis-sidebar-redesign-css";
    if (document.getElementById(id)) return;
    var style = document.createElement("style");
    style.id = id;
    style.textContent = [
        /* Always hide the dock element (floating or pinned). */
        "#desk-dock, .dock { display: none !important; }",

        /* Remove body-class side-effects that pushed the sidebar right. */
        "body.dock-active .body-sidebar-container,",
        "body.dock-pinned .body-sidebar-container { margin-left: 0 !important; }",

        /* On a dock-less layout the sidebar header always shows the module logo. */
        ".body-sidebar .sidebar-header .header-logo { display: inline-flex !important; }",

        /* No dock offset on the sidebar container. */
        ".body-sidebar-container { margin-left: 0 !important; }",
    ].join("\n");
    document.head.appendChild(style);
})();

// ── 2. JS – patch frappe.ui.Sidebar / Dock once the framework is ready ────────
(function patchDock() {
    var MAX_WAIT = 10000;   // give up after 10 s to avoid infinite loops
    var waited  = 0;

    function tryPatch() {
        if (typeof frappe === "undefined" || !frappe.ui || !frappe.ui.Sidebar) {
            waited += 50;
            if (waited < MAX_WAIT) setTimeout(tryPatch, 50);
            return;
        }

        // ── a. Prototype patch – runs before any instance is created ──────────
        //       dock_enabled() returning false makes Dock.refresh() hide itself.
        frappe.ui.Sidebar.prototype.dock_enabled = function () {
            return false;
        };

        // ── b. Header logo – always show module's icon instead of app mark ───
        if (frappe.ui.SidebarHeader) {
            frappe.ui.SidebarHeader.prototype.get_header_logo = function () {
                return this.header_icon;
            };
        }

        // ── c. Neutralise Dock.refresh so a future call never re-enables it ───
        if (frappe.ui.Dock) {
            frappe.ui.Dock.prototype.refresh = function () {
                this.enabled = false;
                $("body").removeClass("dock-active dock-pinned dock-open");
                if (this.$dock) this.$dock.addClass("hidden");
            };
        }

        // ── c. If the sidebar is already live, clean up its dock now ──────────
        if (frappe.app && frappe.app.sidebar) {
            var sidebar = frappe.app.sidebar;

            if (sidebar.dock) {
                sidebar.dock.enabled = false;
                if (sidebar.dock.$dock) sidebar.dock.$dock.addClass("hidden");
            }
            $("body").removeClass("dock-active dock-pinned dock-open");

            // Re-draw the sidebar header so it picks up get_header_logo()
            // which now returns the module icon (no dock → full logo path).
            try {
                if (sidebar.refresh_header) sidebar.refresh_header();
            } catch (e) {
                // Will refresh on next navigation; safe to ignore.
            }
        }

        console.info("[OrbisERP] Dock disabled – single sidebar column active.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", tryPatch);
    } else {
        tryPatch();
    }
})();
"""


# ─── helpers ──────────────────────────────────────────────────────────────────

SITE_ROOT   = "/home/frappe/frappe-bench/sites/frontend"
SITE_CONFIG = os.path.join(SITE_ROOT, "site_config.json")
JS_DEST     = os.path.join(SITE_ROOT, "public", "files", "orbis_sidebar_redesign.js")
JS_URL      = "/files/orbis_sidebar_redesign.js"   # served by the nginx / werkzeug


def write_js_file():
    os.makedirs(os.path.dirname(JS_DEST), exist_ok=True)
    with open(JS_DEST, "w", encoding="utf-8") as f:
        f.write(ORBIS_JS)
    print(f"  Wrote JS → {JS_DEST}")


def patch_site_config():
    with open(SITE_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)

    existing = config.get("app_include_js", [])
    if JS_URL not in existing:
        existing.append(JS_URL)
        config["app_include_js"] = existing
        with open(SITE_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=1)
        print(f"  Patched site_config.json → added {JS_URL}")
    else:
        print(f"  site_config.json already contains {JS_URL} (no change)")


# ─── main ─────────────────────────────────────────────────────────────────────

def run():
    print("\n=== Step 21: OrbisERP Sidebar Redesign ===\n")

    write_js_file()
    patch_site_config()

    frappe.db.commit()
    print("\n✅  Done.\n")
    print("   Hard-refresh the OrbisERP browser tab (Ctrl+Shift+R) to see the")
    print("   single-sidebar layout.  The left dock column will be gone, and")
    print("   the sidebar header will show the active module's icon + name.")
    print("   Module switching continues to work as before.")
    return "Step 21 complete"
