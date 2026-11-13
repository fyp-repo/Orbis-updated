import frappe
import time

def run_tests():
    frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()

    from frappe.core.doctype.user.user import reset_password, check_password_reset_rate_limit

    print("=" * 60)
    print("ORBIS ERP PASSWORD RESET RATE LIMIT & PROFILE BUTTON TESTS")
    print("=" * 60)

    admin_user = "Administrator"
    admin_email = "forw8007@gmail.com"
    purchase_user = "forw8007+purchasemanager@gmail.com"
    sales_user = "forw8007+salesmanager@gmail.com"
    unknown_email = "nonexistent.user.test99@gmail.com"

    # Clean existing rate limit keys in Redis cache
    for email in [admin_email, purchase_user, sales_user, unknown_email]:
        frappe.cache.delete_key(f"rl:pw_reset:{email.lower()}")
    frappe.cache.delete_key("rl:pw_reset:anonymous")

    # -------------------------------------------------------------
    # TEST 1: Administrator Requests 3 OTPs (Allowed), 4th Blocked
    # -------------------------------------------------------------
    print("\n--- TEST 1: Administrator Rate Limit (Max 3 / 60s) ---")
    frappe.set_user("Guest")
    admin_results = []
    for i in range(1, 5):
        try:
            frappe.clear_messages()
            reset_password(admin_user)
            admin_results.append(True)
            print(f"  Attempt {i} for {admin_user}: ALLOWED (Success)")
        except frappe.RateLimitExceededError as e:
            admin_results.append(False)
            print(f"  Attempt {i} for {admin_user}: BLOCKED ({e})")

    assert admin_results == [True, True, True, False], f"Admin attempts failed expectation: {admin_results}"
    print("  >>> TEST 1 PASSED: Administrator allowed 3, 4th strictly blocked.")

    # -------------------------------------------------------------
    # TEST 2: Purchase Manager Requests 3 OTPs (Independent)
    # -------------------------------------------------------------
    print("\n--- TEST 2: Purchase Manager Independent Limit ---")
    pm_results = []
    for i in range(1, 5):
        try:
            frappe.clear_messages()
            reset_password(purchase_user)
            pm_results.append(True)
            print(f"  Attempt {i} for {purchase_user}: ALLOWED (Success)")
        except frappe.RateLimitExceededError as e:
            pm_results.append(False)
            print(f"  Attempt {i} for {purchase_user}: BLOCKED ({e})")

    assert pm_results == [True, True, True, False], f"Purchase Manager failed expectation: {pm_results}"
    print("  >>> TEST 2 PASSED: Purchase Manager was NOT affected by Admin; allowed 3, 4th blocked.")

    # -------------------------------------------------------------
    # TEST 3: Another User (Sales Manager) Requests 3 OTPs (Independent)
    # -------------------------------------------------------------
    print("\n--- TEST 3: Sales Manager Independent Limit ---")
    sales_results = []
    for i in range(1, 5):
        try:
            frappe.clear_messages()
            reset_password(sales_user)
            sales_results.append(True)
            print(f"  Attempt {i} for {sales_user}: ALLOWED (Success)")
        except frappe.RateLimitExceededError as e:
            sales_results.append(False)
            print(f"  Attempt {i} for {sales_user}: BLOCKED ({e})")

    assert sales_results == [True, True, True, False], f"Sales Manager failed expectation: {sales_results}"
    print("  >>> TEST 3 PASSED: Sales Manager had their own independent 3 requests.")

    # -------------------------------------------------------------
    # TEST 4: Email Casing Normalization Security
    # -------------------------------------------------------------
    print("\n--- TEST 4: Case Normalization Security ---")
    # Clean Sales Manager key to test mixed casing
    frappe.cache.delete_key(f"rl:pw_reset:{sales_user}")
    variations = [
        "forw8007+salesmanager@gmail.com",
        "FORW8007+SALESMANAGER@GMAIL.COM",
        "  Forw8007+SalesManager@gmail.com  ",
        "Forw8007+SALESMANAGER@gmail.com"  # 4th should be blocked!
    ]
    casing_results = []
    for i, v in enumerate(variations, 1):
        try:
            frappe.clear_messages()
            reset_password(v)
            casing_results.append(True)
            print(f"  Attempt {i} with '{v}': ALLOWED")
        except frappe.RateLimitExceededError:
            casing_results.append(False)
            print(f"  Attempt {i} with '{v}': BLOCKED (Rate limit enforced across casing)")

    assert casing_results == [True, True, True, False], f"Casing test failed: {casing_results}"
    print("  >>> TEST 4 PASSED: Normalization prevents bypassing limit via casing/spaces.")

    # -------------------------------------------------------------
    # TEST 5: Unknown Email Address Receives Generic Response
    # -------------------------------------------------------------
    print("\n--- TEST 5: Unknown Email Address Handling ---")
    frappe.clear_messages()
    reset_password(unknown_email)
    msg = frappe.message_log[-1] if frappe.message_log else {}
    msg_text = msg.get("message", "") if isinstance(msg, dict) else str(msg)
    print(f"  Response for unknown email: {msg_text}")
    assert "If this email is registered with us" in msg_text, f"Unexpected message: {msg_text}"
    print("  >>> TEST 5 PASSED: Generic response returned without user enumeration.")

    # -------------------------------------------------------------
    # TEST 6: Rolling Window Expiration (Counter Reset)
    # -------------------------------------------------------------
    print("\n--- TEST 6: Rolling Window Expiration Simulation ---")
    # Test check_password_reset_rate_limit with window_seconds=2
    test_short_email = "short.window.user@orbis.test"
    frappe.cache.delete_key(f"rl:pw_reset:{test_short_email}")

    for i in range(1, 4):
        check_password_reset_rate_limit(test_short_email, limit=3, window_seconds=2)
    print("  3 requests made within 2-second window.")

    # 4th should fail
    blocked_ok = False
    try:
        check_password_reset_rate_limit(test_short_email, limit=3, window_seconds=2)
    except frappe.RateLimitExceededError:
        blocked_ok = True
    assert blocked_ok, "4th request was not blocked!"
    print("  4th request within window successfully blocked.")

    # Wait 2.2 seconds for window to roll over
    print("  Waiting 2.2 seconds for rolling window to expire...")
    time.sleep(2.2)

    # Now 3 new requests must be allowed!
    for i in range(1, 4):
        check_password_reset_rate_limit(test_short_email, limit=3, window_seconds=2)
    print("  3 new requests allowed after window expiration!")
    print("  >>> TEST 6 PASSED: Counter automatically resets after window expires.")

    # -------------------------------------------------------------
    # TEST 7: User Profile Password Reset Button (Desk Authenticated)
    # -------------------------------------------------------------
    print("\n--- TEST 7: User Profile Password Reset Button as Administrator ---")
    frappe.set_user("Administrator")

    # Clear rate limit for Purchase Manager
    frappe.cache.delete_key(f"rl:pw_reset:{purchase_user}")

    # Administrator clicks Password Reset while editing Purchase Manager
    frappe.clear_messages()
    reset_password(purchase_user)

    desk_msg = frappe.message_log[-1] if frappe.message_log else {}
    desk_msg_text = desk_msg.get("message", "") if isinstance(desk_msg, dict) else str(desk_msg)
    print(f"  Desk confirmation message: {desk_msg_text}")
    assert purchase_user in desk_msg_text, f"Selected user email not in desk message: {desk_msg_text}"
    assert admin_email not in desk_msg_text or purchase_user == admin_email, "Admin email should not be recipient!"

    # Verify Email Queue has the password reset email for Purchase Manager
    latest_email = frappe.db.sql("""
        SELECT eq.name, eq.sender, eqr.recipient, eq.status
        FROM `tabEmail Queue` eq
        JOIN `tabEmail Queue Recipient` eqr ON eqr.parent = eq.name
        WHERE eqr.recipient = %s
        ORDER BY eq.creation DESC LIMIT 1
    """, (purchase_user,), as_dict=True)

    print(f"  Email Queue Record for {purchase_user}: {latest_email}")
    assert len(latest_email) == 1, "No email queue record found for purchase manager!"
    assert latest_email[0].recipient == purchase_user, f"Wrong recipient: {latest_email[0].recipient}"
    assert latest_email[0].status == "Sent", f"Email status not Sent: {latest_email[0].status}"

    # Verify reset_password_key was set on the selected user
    target_user_doc = frappe.get_doc("User", purchase_user)
    assert target_user_doc.reset_password_key, "reset_password_key was not generated on target user!"
    print(f"  Verified: Target user reset_password_key is generated ({target_user_doc.reset_password_key[:12]}...)")
    print(f"  Verified: Recipient is strictly {target_user_doc.email}, NOT Administrator.")
    print("  >>> TEST 7 PASSED: User Edit Profile button correctly dispatches reset email to target user.")

    # -------------------------------------------------------------
    # TEST 8: Non-Admin Permission Check in Desk
    # -------------------------------------------------------------
    print("\n--- TEST 8: Unauthorized Desk User Access Guard ---")
    frappe.set_user(sales_user)
    unauth_blocked = False
    try:
        reset_password(purchase_user)
    except frappe.PermissionError:
        unauth_blocked = True
        print("  Non-admin user attempting to reset another user: BLOCKED (PermissionError)")
    assert unauth_blocked, "Non-admin user was not blocked from resetting another user!"
    print("  >>> TEST 8 PASSED: Unauthorized users cannot trigger password resets for other accounts.")

    frappe.set_user("Administrator")
    print("\n" + "=" * 60)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

    frappe.destroy()

if __name__ == "__main__":
    run_tests()
