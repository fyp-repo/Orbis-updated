"""
Step 17: Customize Supplier Document Window Three-Dot Menu
===========================================================
Customizes the dropdown menu (three-dot menu) for the Supplier form in Frappe Desk:
1. Retains ONLY requested options:
   - Toggle Sidebar
   - Rename (optional)
   - Reload
   - New Supplier
   - Show Links
   - Settings
   - Customize (Admin only)
2. Hides:
   - Email
   - Duplicate
   - Jump to field
   - Copy to Clipboard
   - Remind Me
   - Undo
   - Redo
   - Edit DocType (Admin only; hidden from regular users)
   - Documentation (optional)
   - Other non-essential action items
"""

import frappe

SCRIPT_NAME = "Orbis Supplier Form Menu"

SCRIPT_CODE = r"""
frappe.ui.form.on('Supplier', {
    refresh: function(frm) {
        setup_supplier_menu(frm);
    }
});

function setup_supplier_menu(frm) {
    if (!frm.page || !frm.page.menu) return;

    function apply_menu_filter() {
        if (!frm.page || !frm.page.menu) return;

        const is_admin = frappe.user_roles && (
            frappe.user_roles.includes('System Manager') || 
            frappe.user_roles.includes('Administrator') ||
            frappe.session.user === 'Administrator'
        );

        // Target items to hide
        const hide_list = [
            'email',
            'duplicate',
            'jump to field',
            'copy to clipboard',
            'remind me',
            'undo',
            'redo',
            'documentation',
            'view audit trail',
            'repeat',
            'follow',
            'unfollow'
        ];

        // Target items to keep
        const keep_list = [
            'toggle sidebar',
            'rename',
            'reload',
            'new supplier',
            'new',
            'show links',
            'settings'
        ];

        if (is_admin) {
            keep_list.push('customize');
            keep_list.push('edit doctype');
            keep_list.push('delete');
        } else {
            hide_list.push('customize');
            hide_list.push('edit doctype');
            hide_list.push('delete');
        }

        // Filter menu items
        frm.page.menu.find('li').each(function(index, elem) {
            const $li = $(elem);
            if ($li.hasClass('divider') || $li.hasClass('dropdown-divider')) {
                return;
            }

            const raw_text = ($li.find('.menu-item-label').text() || $li.find('a').text() || $li.text() || '').trim();
            const text = raw_text.toLowerCase();
            if (!text) return;

            const should_hide = hide_list.some(function(h) { return text === h || text.startsWith(h); });
            const should_keep = keep_list.some(function(k) { return text === k || text.startsWith(k); });

            if (should_hide || !should_keep) {
                $li.addClass('hidden').attr('style', 'display: none !important;');
            } else {
                $li.removeClass('hidden').removeAttr('style');
            }
        });

        // Clean up redundant or leading/trailing dividers
        let prev_divider = true;
        frm.page.menu.find('li').each(function(index, elem) {
            const $li = $(elem);
            const is_divider = $li.hasClass('divider') || $li.hasClass('dropdown-divider');
            const is_hidden = $li.hasClass('hidden') || $li.css('display') === 'none' || ($li.attr('style') && $li.attr('style').indexOf('none') !== -1);

            if (is_hidden) return;

            if (is_divider) {
                if (prev_divider) {
                    $li.addClass('hidden').attr('style', 'display: none !important;');
                } else {
                    $li.removeClass('hidden').removeAttr('style');
                    prev_divider = true;
                }
            } else {
                prev_divider = false;
            }
        });

        // Ensure no trailing divider
        frm.page.menu.find('li').filter(function(index, elem) {
            const $el = $(elem);
            return !($el.hasClass('hidden') || $el.css('display') === 'none' || ($el.attr('style') && $el.attr('style').indexOf('none') !== -1));
        }).last().filter('.divider, .dropdown-divider').addClass('hidden').attr('style', 'display: none !important;');
    }

    apply_menu_filter();
    setTimeout(apply_menu_filter, 50);
    setTimeout(apply_menu_filter, 150);
    setTimeout(apply_menu_filter, 400);

    if (frm.page.menu_btn_group) {
        frm.page.menu_btn_group.off('show.bs.dropdown.supplier_menu').on('show.bs.dropdown.supplier_menu', function() {
            apply_menu_filter();
        });
        frm.page.menu_btn_group.find('button, .dropdown-toggle').off('click.supplier_menu').on('click.supplier_menu', function() {
            setTimeout(apply_menu_filter, 10);
            setTimeout(apply_menu_filter, 100);
        });
    }
}
"""

def run():
    print("--- Configuring Supplier Form Menu Client Script ---")
    if frappe.db.exists("Client Script", SCRIPT_NAME):
        cs = frappe.get_doc("Client Script", SCRIPT_NAME)
        cs.script = SCRIPT_CODE
        cs.enabled = 1
        cs.save(ignore_permissions=True)
        print(f"  Updated existing Client Script: {SCRIPT_NAME}")
    else:
        cs = frappe.get_doc({
            "doctype": "Client Script",
            "name": SCRIPT_NAME,
            "dt": "Supplier",
            "view": "Form",
            "enabled": 1,
            "script": SCRIPT_CODE
        })
        cs.insert(ignore_permissions=True)
        print(f"  Created new Client Script: {SCRIPT_NAME}")

    frappe.clear_cache()
    frappe.db.commit()
    print("  Supplier Form menu customization applied successfully!")
    return "Done"

if __name__ == "__main__":
    run()
