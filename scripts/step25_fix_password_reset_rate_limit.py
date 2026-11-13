"""
Step 25: Fix OrbisERP Password Reset OTP Rate Limiting & User Profile Password Reset Button
==========================================================================================
1. Root Cause Analysis:
   - In standard Frappe (user.py), reset_password was decorated with:
       @rate_limit(limit=get_password_reset_limit, seconds=60 * 60)
   - Because no key parameter was supplied, rate_limiter.py defaulted to identity = ip.
   - In containerized and local deployments, all requests originate from 127.0.0.1.
   - Consequently, all users shared the exact same rate-limit bucket ('rl:reset_password:127.0.0.1:3600').
   - When Administrator triggered 3 requests, the entire IP was blocked for 3600s (1 hour),
     blocking Purchase Manager and all other users prematurely.
   - Furthermore, user.py had `if user_doc.name != "Administrator" and user_doc.enabled:`,
     which silently suppressed password reset emails when requested for Administrator.

2. Fix Implemented:
   - Replaced IP-based rate limiting with an independent, per-user rolling window rate limiter:
     * Window: 60 seconds (rolling 1-minute window).
     * Limit: 3 requests per user.
     * Stored in Redis as a sorted set (ZADD / ZREMRANGEBYSCORE) keyed by:
         rl:pw_reset:{normalized_email}
     * Email normalization: trim whitespace and lowercase.
     * Casing changes (e.g. SalesManager vs salesmanager) map to the exact same bucket.
     * Administrator, Purchase Manager, and other users have completely independent buckets.
     * Unknown email addresses receive generic responses (CWE-204) and are also throttled independently.
   - User Edit Profile 'Reset Password' button:
     * When an Administrator clicks Reset Password while editing another user, the target user's
       registered email is resolved and receives the reset link.
     * The Administrator's email is not used as recipient unless Administrator is the target user.
     * Desk calls provide a clear confirmation message with green indicator.
     * Public / Guest calls return a generic message to prevent user enumeration.
     * Unauthorized non-admin users cannot trigger password resets for other accounts.
"""

import os
import frappe

USER_PY_PATH = "/home/frappe/frappe-bench/apps/frappe/frappe/core/doctype/user/user.py"
USER_JS_PATH = "/home/frappe/frappe-bench/apps/frappe/frappe/core/doctype/user/user.js"

NEW_BACKEND_CODE = '''def check_password_reset_rate_limit(registered_email: str, limit: int = 3, window_seconds: int = 60) -> None:
	"""
	Enforces an independent per-user rolling window rate limit for password reset requests.
	- Each user is identified by their normalized registered ERP email address.
	- Maximum `limit` requests within a rolling `window_seconds` window (3 requests / 60 seconds).
	- Normalizes email address (trimmed and lowercase).
	- Uses Redis sorted sets to maintain independent per-user timestamps.
	- Blocked requests for one user do not affect any other user.
	"""
	import time

	normalized_key = (registered_email or "").strip().lower()
	if not normalized_key:
		normalized_key = "anonymous"

	now = time.time()
	cache_key = frappe.cache.make_key(f"rl:pw_reset:{normalized_key}")

	# 1. Purge timestamps older than the rolling window
	frappe.cache.zremrangebyscore(cache_key, 0, now - window_seconds)

	# 2. Count requests currently within the rolling window
	current_count = frappe.cache.zcard(cache_key)

	if current_count >= limit:
		frappe.throw(
			_("You have exceeded the maximum of {0} password reset requests within {1} seconds. Please wait before trying again.").format(
				limit, window_seconds
			),
			frappe.RateLimitExceededError,
		)

	# 3. Record this request timestamp
	member = f"{now}:{time.time_ns()}"
	frappe.cache.zadd(cache_key, {member: now})
	frappe.cache.expire(cache_key, window_seconds + 5)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reset_password(user: str) -> None:
	"""
	Initiates password reset for a user with independent per-user rate limiting (3 requests / 1 min).
	"""
	if not user:
		frappe.throw(_("User is required"), frappe.ValidationError)

	raw_user = (user or "").strip()
	normalized_input = raw_user.lower()

	# 1. Resolve registered User document
	user_doc = None
	# Try matching by name
	if frappe.db.exists("User", raw_user):
		user_doc = frappe.get_doc("User", raw_user)
	elif frappe.db.exists("User", normalized_input):
		user_doc = frappe.get_doc("User", normalized_input)
	else:
		# Try matching by email field
		matched_name = frappe.db.get_value("User", {"email": normalized_input}, "name")
		if matched_name:
			user_doc = frappe.get_doc("User", matched_name)

	# 2. Determine normalized registered email for rate limiting
	if user_doc:
		registered_email = (user_doc.email or user_doc.name).strip().lower()
	else:
		registered_email = normalized_input

	# 3. Enforce separate rate limit for this specific registered email
	check_password_reset_rate_limit(registered_email, limit=3, window_seconds=60)

	# 4. Check permissions if request is from an authenticated user in Desk
	is_desk_request = (frappe.session.user != "Guest")
	if is_desk_request:
		has_system_manager = "System Manager" in frappe.get_roles()
		is_self = (user_doc and frappe.session.user == user_doc.name)
		if not (has_system_manager or is_self):
			frappe.throw(_("You are not authorized to reset password for this user."), frappe.PermissionError)

	# 5. Handle password reset link generation and email dispatch
	email_sent = False
	if user_doc and user_doc.enabled:
		target_email = (user_doc.email or "").strip()
		if not target_email:
			if is_desk_request:
				frappe.throw(_("User {0} does not have an email address configured.").format(user_doc.name))
		else:
			try:
				user_doc.validate_reset_password()
				user_doc._reset_password(send_email=True)
				# Commit transaction to trigger after_commit hooks and immediately send email
				frappe.db.commit()
				email_sent = True
			except frappe.OutgoingEmailError:
				frappe.clear_messages()
				frappe.log_error(title="Password reset email could not be sent", message=frappe.get_traceback())
				if is_desk_request:
					frappe.throw(_("Failed to send password reset email. Please check your email configuration."))
			except Exception:
				frappe.clear_messages()
				frappe.log_error(title="Password reset failed unexpectedly", message=frappe.get_traceback())
				if is_desk_request:
					frappe.throw(_("An unexpected error occurred while resetting password."))

	# 6. Response messaging
	if is_desk_request and user_doc:
		if not user_doc.enabled:
			frappe.throw(_("Cannot reset password for disabled user {0}.").format(user_doc.name))
		target_email = user_doc.email or user_doc.name
		frappe.msgprint(
			msg=_("Password reset instructions have been sent to {0}.").format(target_email),
			title=_("Password Reset Sent"),
			indicator="green",
		)
	else:
		# For Guest / public requests, always return generic response (CWE-204 prevention)
		frappe.msgprint(
			msg=_(
				"If this email is registered with us, we have sent password reset instructions to it. Please check your inbox."
			),
			title=_("Password Reset"),
		)
'''


def patch_user_py():
	print("--- 1. Patching user.py ---")
	with open(USER_PY_PATH, "r", encoding="utf-8") as f:
		content = f.read()

	target_marker = '@frappe.whitelist(allow_guest=True, methods=["POST"])\n@rate_limit(limit=get_password_reset_limit, seconds=60 * 60)\ndef reset_password(user: str) -> None:'

	if "check_password_reset_rate_limit" in content:
		print("  user.py is already patched with check_password_reset_rate_limit.")
		return

	if target_marker not in content:
		print("  ERROR: Target marker not found in user.py!")
		return

	# Find end of reset_password function (before change_password)
	start_idx = content.find(target_marker)
	end_marker = '@frappe.whitelist(methods=["POST"])\ndef change_password('
	end_idx = content.find(end_marker, start_idx)

	if end_idx == -1:
		print("  ERROR: End marker for reset_password not found!")
		return

	# Backup original file
	backup_path = USER_PY_PATH + ".bak"
	if not os.path.exists(backup_path):
		with open(backup_path, "w", encoding="utf-8") as f:
			f.write(content)
		print(f"  Backed up original user.py to {backup_path}")

	# Replace with new code
	new_content = content[:start_idx] + NEW_BACKEND_CODE + "\n\n\n" + content[end_idx:]
	with open(USER_PY_PATH, "w", encoding="utf-8") as f:
		f.write(new_content)
	print("  Successfully updated user.py with independent rolling rate limiting.")


def patch_user_js():
	print("--- 2. Patching user.js ---")
	with open(USER_JS_PATH, "r", encoding="utf-8") as f:
		content = f.read()

	old_btn = '''			frm.add_custom_button(
				__("Reset Password"),
				function () {
					frappe.call({
						method: "frappe.core.doctype.user.user.reset_password",
						args: {
							user: frm.doc.name,
						},
					});
				},
				__("Password")
			);'''

	new_btn = '''			if (cint(frm.doc.enabled)) {
				frm.add_custom_button(
					__("Reset Password"),
					function () {
						frappe.call({
							method: "frappe.core.doctype.user.user.reset_password",
							args: {
								user: frm.doc.name,
							},
							freeze: true,
							freeze_message: __("Sending password reset email..."),
						});
					},
					__("Password")
				);
			}'''

	if 'freeze_message: __("Sending password reset email...")' in content:
		print("  user.js is already patched.")
		return

	if old_btn in content:
		backup_path = USER_JS_PATH + ".bak"
		if not os.path.exists(backup_path):
			with open(backup_path, "w", encoding="utf-8") as f:
				f.write(content)
			print(f"  Backed up original user.js to {backup_path}")

		content = content.replace(old_btn, new_btn)
		with open(USER_JS_PATH, "w", encoding="utf-8") as f:
			f.write(content)
		print("  Successfully updated user.js button handler.")
	else:
		print("  Notice: Custom button block structure differed in user.js; skipping.")


def run():
	os.makedirs("/home/frappe/logs", exist_ok=True)
	os.chdir("/home/frappe/frappe-bench/sites")
	if not frappe.db:
		frappe.init(site="frontend", sites_path="/home/frappe/frappe-bench/sites")
		frappe.connect()

	patch_user_py()
	patch_user_js()

	# Clear site cache
	try:
		frappe.clear_cache()
	except Exception as e:
		print(f"Cache notice: {e}")

	print("\n[Step 25 Applied] Backend rate limiting and User profile button patched.")
	return "[Step 25 Complete]"


if __name__ == "__main__":
	run()
	frappe.destroy()

