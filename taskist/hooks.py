app_name = "taskist"
app_title = "Taskist"
app_publisher = "Taskist"
app_description = "Task Management SPA"
app_email = "dev@taskist.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# Registers Taskist as an app with a route, so users whose Default App is
# "taskist" (e.g. Brycom technicians) land on /taskist after login.
add_to_apps_screen = [
	{
		"name": "taskist",
		"logo": "/assets/taskist/logo.png",
		"title": "Taskist",
		"route": "/taskist",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/taskist/css/taskist.css"
# app_include_js = "/assets/taskist/js/taskist.js"

# include js, css files in header of web template
# web_include_css = "/assets/taskist/css/taskist.css"
# web_include_js = "/assets/taskist/js/taskist.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "taskist/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "taskist/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "taskist.utils.jinja_methods",
# 	"filters": "taskist.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "taskist.install.before_install"
# after_install = "taskist.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "taskist.uninstall.before_uninstall"
# after_uninstall = "taskist.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "taskist.utils.before_app_install"
# after_app_install = "taskist.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "taskist.utils.before_app_uninstall"
# after_app_uninstall = "taskist.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "taskist.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------

doc_events = {
	"Task": {
		"before_save": "taskist.brycom.task_before_save",
		"after_insert": "taskist.api.notify_task_change",
		"on_update": "taskist.api.notify_task_change",
	},
	# Brycom installation workflow (no-ops on sites without these doctypes)
	"Installation Job": {
		"before_save": "taskist.brycom.installation_job_validate",
		"on_update": "taskist.brycom.installation_job_on_update",
	},
	"Sales Invoice": {
		"on_submit": "taskist.brycom.sales_invoice_on_submit",
	},
	"User": {
		"before_save": "taskist.brycom.user_before_save",
	},
}

permission_query_conditions = {
	"Task": "taskist.brycom.task_query",
	"Installation Job": "taskist.brycom.installation_job_query",
}

has_permission = {
	"Task": "taskist.brycom.task_has_permission",
	"Installation Job": "taskist.brycom.installation_job_has_permission",
}


# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"taskist.api.create_recurring_tasks"
	],
}

fixtures = [
	{"dt": "Custom Field", "filters": [["name", "like", "Task-taskist_%"]]},
]

after_install = "taskist.setup.after_install"

# Testing
# -------

# before_tests = "taskist.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "taskist.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "taskist.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "taskist.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["taskist.utils.before_request"]
# after_request = ["taskist.utils.after_request"]

# Job Events
# ----------
# before_job = ["taskist.utils.before_job"]
# after_job = ["taskist.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"taskist.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

website_route_rules = [
	{"from_route": "/taskist/<path:app_path>", "to_route": "taskist"},
]

add_to_apps_screen = [
	{
		"name": "taskist",
		"logo": "/assets/taskist/logo.png",
		"title": "Taskist",
		"route": "/taskist",
	}
]

