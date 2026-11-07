import frappe
from frappe.utils import nowdate, now_datetime, getdate, cint, flt
import json
import re


def _normalize_date(dt_value):
	"""Convert Datetime field value to 'YYYY-MM-DD' date string.

	Frappe Datetime fields return values like '2026-02-21 00:00:00'.
	This normalizes them to plain date strings for the frontend.
	"""
	if not dt_value:
		return None
	s = str(dt_value)
	# Return first 10 chars: 'YYYY-MM-DD'
	return s[:10] if len(s) >= 10 else s


def _normalize_datetime(dt_value):
	"""Convert Datetime field value, preserving time when non-zero.

	Returns 'YYYY-MM-DD HH:MM:SS' if time portion is non-zero,
	otherwise returns 'YYYY-MM-DD'.
	"""
	if not dt_value:
		return None
	s = str(dt_value)
	if len(s) > 10:
		time_part = s[11:].strip()
		if time_part and time_part != "00:00:00":
			return s[:19]
	return s[:10] if len(s) >= 10 else s


@frappe.whitelist()
def get_tasks(
	filters=None,
	project=None,
	assigned_to=None,
	include_completed=0,
	order_by="taskist_sort_order asc, modified desc",
	page_length=100,
	start=0,
):
	"""Get tasks with all native + Taskist fields."""
	conditions = {"is_template": 0}

	if filters:
		if isinstance(filters, str):
			filters = json.loads(filters)
		conditions.update(filters)

	if project:
		conditions["project"] = project

	if not cint(include_completed):
		conditions["status"] = ["not in", ["Completed", "Cancelled", "Template"]]

	# Native Task fields + Taskist custom fields
	fields = [
		"name", "subject", "status", "priority", "project", "parent_task",
		"exp_start_date", "exp_end_date", "expected_time", "progress",
		"color", "is_group", "is_milestone", "type", "task_weight",
		"completed_by", "completed_on", "description",
		"act_start_date", "act_end_date", "actual_time",
		"total_costing_amount", "total_billing_amount",
		"taskist_sort_order",
		"taskist_is_recurring", "taskist_recurrence_rule",
		"_assign", "_user_tags", "modified", "creation",
	]
	# Brycom installation link (only on sites that have the custom field)
	if frappe.get_meta("Task").has_field("custom_installation_job"):
		fields.append("custom_installation_job")

	pl = cint(page_length)
	tasks = frappe.get_list(
		"Task",
		filters=conditions,
		fields=fields,
		order_by=order_by,
		page_length=pl or 0,
		start=cint(start),
	)

	if assigned_to:
		tasks = [t for t in tasks if t.get("_assign") and assigned_to in t["_assign"]]

	# Normalize Datetime fields for the frontend (preserve time when non-zero)
	for task in tasks:
		task["exp_start_date"] = _normalize_datetime(task.get("exp_start_date"))
		task["exp_end_date"] = _normalize_datetime(task.get("exp_end_date"))
		task["act_start_date"] = _normalize_date(task.get("act_start_date"))
		task["act_end_date"] = _normalize_date(task.get("act_end_date"))
		task["completed_on"] = _normalize_date(task.get("completed_on"))

	# Enrich tasks with last comment info
	task_names = [t.name for t in tasks]
	if task_names:
		comments = frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Task",
				"reference_name": ["in", task_names],
				"comment_type": "Comment",
			},
			fields=["reference_name", "content", "creation"],
			order_by="creation desc",
		)

		# Group by task and pick latest
		latest_comments = {}
		for c in comments:
			if c.reference_name not in latest_comments:
				latest_comments[c.reference_name] = c

		for task in tasks:
			comment = latest_comments.get(task.name)
			if comment:
				plain = re.sub(r"<[^>]+>", "", comment.content or "")
				task["_last_comment"] = plain[:50]
				task["_last_comment_at"] = str(comment.creation)
			else:
				task["_last_comment"] = None
				task["_last_comment_at"] = None

	return tasks


@frappe.whitelist()
def quick_create_task(
	subject,
	project=None,
	priority="Medium",
	status="Open",
	parent_task=None,
	exp_start_date=None,
	exp_end_date=None,
	assigned_to=None,
	tags=None,
):
	"""Quickly create a task with minimal input."""
	task = frappe.new_doc("Task")
	task.subject = subject
	task.priority = priority
	task.status = status

	if project:
		task.project = project
	if parent_task:
		task.parent_task = parent_task
		# Ensure the parent is marked as a group task (required by ERPNext)
		parent_is_group = frappe.db.get_value("Task", parent_task, "is_group")
		if not parent_is_group:
			frappe.db.set_value("Task", parent_task, "is_group", 1)
	if exp_start_date:
		task.exp_start_date = exp_start_date
	if exp_end_date:
		task.exp_end_date = exp_end_date

	task.insert(ignore_permissions=False)

	if assigned_to:
		if isinstance(assigned_to, str):
			assigned_to = json.loads(assigned_to) if assigned_to.startswith("[") else [assigned_to]
		for user in assigned_to:
			frappe.desk.form.assign_to.add(
				{"doctype": "Task", "name": task.name, "assign_to": [user]}
			)

	if tags:
		if isinstance(tags, str):
			tags = json.loads(tags) if tags.startswith("[") else [tags]
		for tag in tags:
			task.add_tag(tag)

	return task


@frappe.whitelist()
def update_task_status(task_name, status, sort_order=None):
	"""Update a task's status (used by kanban drag-drop and list toggle)."""
	task = frappe.get_doc("Task", task_name)
	task.status = status
	if sort_order is not None:
		task.taskist_sort_order = cint(sort_order)
	task.save(ignore_permissions=False)
	return {"name": task.name, "status": task.status, "sort_order": task.taskist_sort_order}


@frappe.whitelist()
def update_task_dates(task_name, exp_start_date=None, exp_end_date=None):
	"""Update a task's expected start/end dates (used by calendar drag-drop)."""
	doc = frappe.get_doc("Task", task_name)
	if exp_start_date is not None:
		doc.exp_start_date = exp_start_date or None
	if exp_end_date is not None:
		doc.exp_end_date = exp_end_date or None
	doc.save(ignore_permissions=False)
	return {"name": doc.name, "exp_start_date": str(doc.exp_start_date), "exp_end_date": str(doc.exp_end_date)}


@frappe.whitelist()
def search_projects(query="", page_length=20):
	"""Search projects for task assignment."""
	filters = {"status": "Open"}
	if query:
		filters["name"] = ["like", f"%{query}%"]

	return frappe.get_list(
		"Project",
		filters=filters,
		fields=["name"],
		order_by="name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def search_task_types(query="", page_length=20):
	"""Search task types."""
	filters = {}
	if query:
		filters["name"] = ["like", f"%{query}%"]

	return frappe.get_list(
		"Task Type",
		filters=filters,
		fields=["name"],
		order_by="name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def create_task_type(type_name):
	"""Create a new Task Type on the fly."""
	if frappe.db.exists("Task Type", type_name):
		return {"name": type_name}
	doc = frappe.new_doc("Task Type")
	doc.__newname = type_name
	doc.insert(ignore_permissions=False)
	return {"name": doc.name}


@frappe.whitelist()
def search_customers(query="", page_length=20):
	"""Search ERPNext customers for project assignment."""
	filters = {"disabled": 0}
	or_filters = {}
	if query:
		or_filters = {
			"customer_name": ["like", f"%{query}%"],
			"name": ["like", f"%{query}%"],
		}

	return frappe.get_list(
		"Customer",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "customer_name"],
		order_by="customer_name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def search_companies(query="", page_length=20):
	"""Search ERPNext companies."""
	filters = {}
	if query:
		filters["name"] = ["like", f"%{query}%"]

	return frappe.get_list(
		"Company",
		filters=filters,
		fields=["name"],
		order_by="name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def search_project_types(query="", page_length=20):
	"""Search project types."""
	filters = {}
	if query:
		filters["name"] = ["like", f"%{query}%"]

	return frappe.get_list(
		"Project Type",
		filters=filters,
		fields=["name"],
		order_by="name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def search_project_templates(query="", page_length=20):
	"""Search project templates."""
	filters = {}
	if query:
		filters["name"] = ["like", f"%{query}%"]

	return frappe.get_list(
		"Project Template",
		filters=filters,
		fields=["name"],
		order_by="name asc",
		page_length=cint(page_length),
	)


@frappe.whitelist()
def create_project_type(type_name):
	"""Create a new Project Type on the fly."""
	if frappe.db.exists("Project Type", type_name):
		return {"name": type_name}
	doc = frappe.new_doc("Project Type")
	doc.project_type = type_name
	doc.insert(ignore_permissions=False)
	return {"name": doc.name}


@frappe.whitelist()
def get_summary():
	"""Get per-user task summary: pending, completed today, completed this week, overdue."""
	today = getdate(nowdate())
	# Monday of the current week
	week_start = today - __import__("datetime").timedelta(days=today.weekday())

	tasks = frappe.get_list(
		"Task",
		filters={"is_template": 0, "status": ["not in", ["Cancelled", "Template"]]},
		fields=["name", "status", "exp_end_date", "completed_on", "_assign"],
		page_length=0,
	)

	# Per-user accumulators: {email: {pending, completed_today, completed_week, overdue}}
	user_stats = {}

	def ensure_user(email):
		if email not in user_stats:
			user_stats[email] = {"pending": 0, "completed_today": 0, "completed_week": 0, "overdue": 0}

	totals = {"pending": 0, "completed_today": 0, "completed_week": 0, "overdue": 0, "unassigned": 0}

	for t in tasks:
		assignees = []
		if t._assign:
			try:
				assignees = json.loads(t._assign)
			except (json.JSONDecodeError, TypeError):
				pass

		is_pending = t.status not in ("Completed", "Cancelled", "Template")
		is_completed = t.status == "Completed"

		completed_date = getdate(t.completed_on) if t.completed_on else None
		is_completed_today = is_completed and completed_date == today
		is_completed_week = is_completed and completed_date and completed_date >= week_start

		due_date = getdate(t.exp_end_date) if t.exp_end_date else None
		is_overdue = is_pending and due_date is not None and due_date < today

		if is_pending:
			totals["pending"] += 1
		if is_completed_today:
			totals["completed_today"] += 1
		if is_completed_week:
			totals["completed_week"] += 1
		if is_overdue:
			totals["overdue"] += 1
		if is_pending and not assignees:
			totals["unassigned"] += 1

		for email in assignees:
			ensure_user(email)
			if is_pending:
				user_stats[email]["pending"] += 1
			if is_completed_today:
				user_stats[email]["completed_today"] += 1
			if is_completed_week:
				user_stats[email]["completed_week"] += 1
			if is_overdue:
				user_stats[email]["overdue"] += 1

	# Resolve full names
	users = []
	for email, stats in sorted(user_stats.items()):
		full_name = frappe.db.get_value("User", email, "full_name") or email
		users.append({"email": email, "full_name": full_name, **stats})

	return {"totals": totals, "users": users}


@frappe.whitelist()
def search_users(query="", page_length=10):
	"""Search ERPNext users for task assignment."""
	filters = {"enabled": 1, "user_type": "System User"}
	if query:
		filters["full_name"] = ["like", f"%{query}%"]

	users = frappe.get_list(
		"User",
		filters=filters,
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		page_length=cint(page_length),
	)
	return users


@frappe.whitelist()
def assign_task(task_name, user):
	"""Assign a user to a task."""
	from frappe.desk.form.assign_to import add as assign_add
	assign_add({"doctype": "Task", "name": task_name, "assign_to": [user]})
	return get_task_assignees(task_name)


@frappe.whitelist()
def unassign_task(task_name, user):
	"""Remove a user assignment from a task."""
	from frappe.desk.form.assign_to import remove as assign_remove
	assign_remove("Task", task_name, user)
	return get_task_assignees(task_name)


@frappe.whitelist()
def get_task_comments(task_name):
	"""Get comments for a task. Checks Task read access instead of Comment DocType permissions."""
	frappe.has_permission("Task", doc=task_name, throw=True)
	return frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Task",
			"reference_name": task_name,
			"comment_type": "Comment",
		},
		fields=["name", "content", "comment_by", "creation"],
		order_by="creation asc",
		limit=50,
	)


@frappe.whitelist()
def add_task_comment(task_name, content):
	"""Add a comment to a task. Requires Task write access."""
	frappe.has_permission("Task", "write", doc=task_name, throw=True)
	comment = frappe.new_doc("Comment")
	comment.comment_type = "Comment"
	comment.reference_doctype = "Task"
	comment.reference_name = task_name
	comment.content = content
	comment.insert(ignore_permissions=True)
	return {
		"name": comment.name,
		"content": comment.content,
		"comment_by": comment.comment_by,
		"creation": str(comment.creation),
	}


def get_task_assignees(task_name):
	"""Get list of users assigned to a task."""
	assign_str = frappe.db.get_value("Task", task_name, "_assign")
	if not assign_str:
		return []
	try:
		emails = json.loads(assign_str)
	except (json.JSONDecodeError, TypeError):
		return []

	users = []
	for email in emails:
		full_name = frappe.db.get_value("User", email, "full_name") or email
		users.append({"email": email, "full_name": full_name})
	return users


@frappe.whitelist()
def get_attachments(task_name):
	"""Get file attachments for a task."""
	files = frappe.get_list(
		"File",
		filters={
			"attached_to_doctype": "Task",
			"attached_to_name": task_name,
		},
		fields=["name", "file_name", "file_url", "thumbnail_url", "file_size", "is_private"],
		order_by="creation desc",
	)

	IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
	for f in files:
		ext = (f.file_name or "").rsplit(".", 1)[-1].lower() if f.file_name else ""
		f["file_ext"] = ext
		f["is_image"] = f".{ext}" in IMAGE_EXTS

	return files


@frappe.whitelist()
def remove_attachment(file_name):
	"""Remove a file attachment."""
	frappe.delete_doc("File", file_name, ignore_permissions=False)
	return {"success": True}


@frappe.whitelist()
def get_child_tasks(parent_task):
	"""Get child tasks of a parent task."""
	tasks = frappe.get_list(
		"Task",
		filters={"parent_task": parent_task, "is_template": 0},
		fields=[
			"name", "subject", "status", "priority",
			"is_group", "is_milestone", "progress", "exp_end_date",
		],
		order_by="modified desc",
	)
	for task in tasks:
		task["exp_end_date"] = _normalize_date(task.get("exp_end_date"))
	return tasks


def notify_task_change(doc, method=None):
	"""Broadcast task changes via realtime for multi-user sync."""
	frappe.publish_realtime(
		"taskist_update",
		{
			"task": doc.name,
			"action": method or "update",
			"status": doc.status,
			"modified_by": frappe.session.user,
		},
		after_commit=True,
	)


def create_recurring_tasks():
	"""Scheduler job: create recurring tasks based on JSON recurrence rules.

	Recurrence rule format (JSON):
	{
		"frequency": "daily" | "weekly" | "monthly",
		"weekdays": [0-6],  // 0=Sunday, 1=Monday, ...
		"monthDay": 1-31,
		"time": "HH:MM"
	}
	"""
	import datetime

	today = getdate(nowdate())
	weekday = today.weekday()  # 0=Monday in Python
	# Convert to JS-style: 0=Sunday
	js_weekday = (weekday + 1) % 7

	recurring_tasks = frappe.get_list(
		"Task",
		filters={
			"taskist_is_recurring": 1,
			"taskist_recurrence_rule": ["is", "set"],
			"status": "Completed",
		},
		fields=["name", "subject", "project", "priority", "taskist_recurrence_rule", "parent_task"],
	)

	for task_data in recurring_tasks:
		try:
			rule = json.loads(task_data.taskist_recurrence_rule)
		except (json.JSONDecodeError, TypeError):
			continue

		should_create = False
		frequency = rule.get("frequency", "daily")

		if frequency == "daily":
			should_create = True
		elif frequency == "weekly":
			weekdays = rule.get("weekdays", [])
			should_create = js_weekday in weekdays
		elif frequency == "monthly":
			month_day = rule.get("monthDay", 1)
			should_create = today.day == month_day

		if not should_create:
			continue

		# Check if already created today (avoid duplicates)
		existing = frappe.get_list(
			"Task",
			filters={
				"subject": task_data.subject,
				"creation": [">=", f"{today} 00:00:00"],
				"taskist_is_recurring": 1,
				"status": ["!=", "Completed"],
			},
			limit=1,
		)
		if existing:
			continue

		new_task = frappe.new_doc("Task")
		new_task.subject = task_data.subject
		new_task.project = task_data.project
		new_task.priority = task_data.priority
		new_task.parent_task = task_data.parent_task
		new_task.status = "Open"
		new_task.taskist_is_recurring = 1
		new_task.taskist_recurrence_rule = task_data.taskist_recurrence_rule
		new_task.exp_start_date = nowdate()
		new_task.insert(ignore_permissions=True)

	frappe.db.commit()
