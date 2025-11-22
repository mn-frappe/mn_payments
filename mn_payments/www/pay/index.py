import frappe


def get_context(context):
	context.no_cache = True
	context.csrf_token = frappe.sessions.get_csrf_token()
	return context
