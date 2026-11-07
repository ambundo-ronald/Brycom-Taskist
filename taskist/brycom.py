"""Brycom installation workflow.

Ties the Brycom "Installation Job" doctype (created on the Brycomm ERP site) to
Taskist tasks, moves serial-numbered tracker stock as the job progresses and
creates the installation invoice.

Every hook here is a no-op on sites that do not have the Installation Job
doctype or the Task custom fields, so the app stays safe to install elsewhere.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now, today

TECH_WH = "With Technicians - Brycom"
SUB_WH = "Installed - Subscription - Brycom"
RET_WH = "Returned - Testing - Brycom"

OPEN_STATES = ("Draft", "Assigned", "Accepted")
STAFF_ROLES = {
	"System Manager",
	"Sales User",
	"Sales Manager",
	"Stock User",
	"Stock Manager",
	"Accounts User",
	"Accounts Manager",
	"Projects User",
	"Projects Manager",
	"HR User",
	"HR Manager",
}
TECH_EDITABLE = (
	"vehicle_reg",
	"vehicle_make_model",
	"sim_number",
	"registered_owner",
	"financier",
	"chassis_no",
	"engine_no",
	"colour",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _enabled():
	return frappe.db.exists("DocType", "Installation Job")


def is_technician_only(user=None):
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return False
	roles = set(frappe.get_roles(user))
	return "Technician" in roles and not (roles & STAFF_ROLES)


def _move(job, rows, s_wh, t_wh, remark):
	"""Submit one Material Transfer for the given device rows."""
	grouped = {}
	for d in rows:
		grouped.setdefault(d.item_code, []).append(d.serial_no)

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Transfer"
	se.purpose = "Material Transfer"
	se.company = job.company
	se.remarks = remark
	for item_code, serials in grouped.items():
		se.append(
			"items",
			{
				"item_code": item_code,
				"qty": len(serials),
				"s_warehouse": s_wh,
				"t_warehouse": t_wh,
				"use_serial_batch_fields": 1,
				"serial_no": "\n".join(serials),
			},
		)
	se.flags.ignore_permissions = True
	se.insert()
	se.submit()
	return se.name


def _set_job(job, field, value):
	frappe.db.set_value("Installation Job", job.name, field, value, update_modified=False)
	job.set(field, value)


def _set_task(job, values):
	if job.task and frappe.db.exists("Task", job.task):
		frappe.db.set_value("Task", job.task, values, update_modified=False)


def _close_todos(job, status):
	if not job.task:
		return
	for name in frappe.get_all(
		"ToDo",
		filters={"reference_type": "Task", "reference_name": job.task, "status": "Open"},
		pluck="name",
	):
		frappe.db.set_value("ToDo", name, "status", status, update_modified=False)


def _job_for_task(task_name):
	job_name = frappe.db.get_value("Task", task_name, "custom_installation_job")
	if not job_name:
		frappe.throw(_("This task is not linked to an Installation Job."))
	return frappe.get_doc("Installation Job", job_name)


def _check_technician(job):
	user = frappe.session.user
	if job.technician != user and "System Manager" not in frappe.get_roles(user):
		frappe.throw(_("Only the assigned technician can do this."), frappe.PermissionError)


def _set_state(job, state):
	job.workflow_state = state
	job.flags.ignore_permissions = True
	job.save()


# ---------------------------------------------------------------------------
# Installation Job events
# ---------------------------------------------------------------------------


def installation_job_validate(doc, method=None):
	old = doc.get_doc_before_save()
	prev = old.workflow_state if old else None
	state = doc.workflow_state or "Draft"

	total = 0
	for c in doc.charges:
		c.amount = flt(c.qty) * flt(c.rate)
		total += c.amount
	doc.total_amount = total

	if old and prev not in (None, "Draft", "Assigned"):
		if sorted(d.serial_no for d in old.devices) != sorted(d.serial_no for d in doc.devices):
			frappe.throw(_("Devices cannot be changed after the technician has accepted them."))

	seen = set()
	for d in doc.devices:
		if d.serial_no in seen:
			frappe.throw(_("Serial No {0} is listed twice.").format(d.serial_no))
		seen.add(d.serial_no)
		sn = frappe.db.get_value("Serial No", d.serial_no, ["item_code", "warehouse"], as_dict=True)
		if not sn:
			frappe.throw(_("Serial No {0} does not exist.").format(d.serial_no))
		if sn.item_code != d.item_code:
			frappe.throw(
				_("Serial No {0} belongs to item {1}, not {2}.").format(d.serial_no, sn.item_code, d.item_code)
			)
		if state in ("Draft", "Assigned"):
			if sn.warehouse != doc.source_warehouse:
				frappe.throw(
					_("Serial No {0} is not in {1} (it is in {2}).").format(
						d.serial_no, doc.source_warehouse, sn.warehouse or _("no warehouse")
					)
				)
			other = frappe.db.sql(
				"""select j.name from `tabInstallation Job Device` d
				join `tabInstallation Job` j on j.name = d.parent
				where d.serial_no = %s and j.name != %s and j.workflow_state in %s""",
				(d.serial_no, doc.name or "", OPEN_STATES),
			)
			if other:
				frappe.throw(_("Serial No {0} is already on open job {1}.").format(d.serial_no, other[0][0]))

	if state == prev:
		return

	if state == "Assigned":
		if not doc.technician:
			frappe.throw(_("Select a technician before assigning the job."))
		if not doc.devices:
			frappe.throw(_("Add at least one device before assigning the job."))
	elif state == "Accepted":
		doc.accepted_by = frappe.session.user
		doc.accepted_on = now()
	elif state == "Installed":
		missing = [d.serial_no for d in doc.devices if not d.vehicle_reg]
		if missing:
			frappe.throw(_("Enter the vehicle reg no for: {0}").format(", ".join(missing)))
		doc.installed_on = now()
		for d in doc.devices:
			d.device_status = "Installed"
	elif state == "Returned":
		for d in doc.devices:
			d.device_status = "Returned"
	elif state == "Uninstalled":
		subs = [d for d in doc.devices if d.supply_type == "Subscription"]
		if not subs:
			frappe.throw(_("This job has no Brycomm-owned (Subscription) devices to uninstall."))
		for d in subs:
			d.device_status = "Uninstalled"


def installation_job_on_update(doc, method=None):
	old = doc.get_doc_before_save()
	prev = old.workflow_state if old else None
	state = doc.workflow_state
	if not state or state == prev:
		return

	if state == "Assigned":
		_create_task(doc)

	elif state == "Draft" and prev == "Assigned":
		_set_task(doc, {"status": "Cancelled"})
		_close_todos(doc, "Cancelled")
		_set_job(doc, "task", None)

	elif state == "Accepted":
		name = _move(
			doc, doc.devices, doc.source_warehouse, TECH_WH,
			_("Handed to technician {0} for {1}").format(doc.technician, doc.name),
		)
		_set_job(doc, "handover_entry", name)
		_set_task(doc, {"custom_receipt_accepted": 1, "status": "Working"})

	elif state == "Installed":
		subs = [d for d in doc.devices if d.supply_type == "Subscription"]
		if subs:
			name = _move(
				doc, subs, TECH_WH, SUB_WH,
				_("Brycomm-owned devices installed for {0} ({1})").format(doc.customer, doc.name),
			)
			_set_job(doc, "subscription_entry", name)
		_set_task(doc, {"status": "Completed"})
		_close_todos(doc, "Closed")

	elif state == "Returned":
		name = _move(
			doc, doc.devices, TECH_WH, doc.source_warehouse,
			_("Devices returned unused from {0}").format(doc.name),
		)
		_set_job(doc, "return_entry", name)
		_set_task(doc, {"status": "Cancelled"})
		_close_todos(doc, "Cancelled")

	elif state == "Uninstalled":
		subs = [d for d in doc.devices if d.supply_type == "Subscription"]
		name = _move(
			doc, subs, SUB_WH, RET_WH,
			_("Brycomm-owned devices uninstalled from {0} ({1})").format(doc.customer, doc.name),
		)
		_set_job(doc, "return_entry", name)


def _create_task(job):
	lines = [
		"{0} - {1} ({2})".format(
			d.item_code, d.serial_no, "Sold" if d.supply_type == "Sold" else "Brycomm-owned"
		)
		for d in job.devices
	]
	customer = job.customer_name or job.customer
	desc = (
		"<p><b>Customer:</b> {0}<br><b>Phone:</b> {1}<br><b>Location:</b> {2}<br>"
		"<b>Date:</b> {3}<br><b>Job:</b> {4}</p>"
	).format(customer, job.contact_phone or "", job.location or "", job.installation_date or "", job.name)

	task = frappe.new_doc("Task")
	task.update(
		{
			"subject": _("Install trackers: {0} ({1})").format(customer, job.name),
			"status": "Open",
			"priority": "Medium",
			"company": job.company,
			"project": job.project,
			"exp_start_date": job.installation_date,
			"description": desc,
			"custom_installation_job": job.name,
			"custom_device_summary": "\n".join(lines),
		}
	)
	task.insert(ignore_permissions=True)

	frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": job.technician,
			"reference_type": "Task",
			"reference_name": task.name,
			"description": task.subject,
			"date": job.installation_date,
			"assigned_by": frappe.session.user,
			"priority": "Medium",
		}
	).insert(ignore_permissions=True)
	_set_job(job, "task", task.name)


# ---------------------------------------------------------------------------
# Task events (desk tick / status change keep the job in step)
# ---------------------------------------------------------------------------


def task_before_save(doc, method=None):
	if doc.is_new() or not doc.get("custom_installation_job"):
		return
	if frappe.flags.in_installation_sync:
		return

	old = doc.get_doc_before_save()
	was_accepted = cint(old.custom_receipt_accepted) if old else 0
	was_completed = bool(old and old.status == "Completed")
	job_name = doc.custom_installation_job
	job_state = frappe.db.get_value("Installation Job", job_name, "workflow_state")

	if was_accepted and not cint(doc.custom_receipt_accepted):
		frappe.throw(_("Receipt of the devices has already been accepted and cannot be undone."))

	if cint(doc.custom_receipt_accepted) and not was_accepted:
		if job_state != "Assigned":
			frappe.throw(
				_("Installation Job {0} is {1}, so receipt cannot be accepted now.").format(job_name, job_state)
			)
		job = frappe.get_doc("Installation Job", job_name)
		_check_technician(job)
		_set_state(job, "Accepted")
		job_state = "Accepted"
		if doc.status == "Open":
			doc.status = "Working"

	if doc.status == "Completed" and not was_completed:
		if not cint(doc.custom_receipt_accepted):
			frappe.throw(_("Accept receipt of the devices before completing the installation."))
		if job_state == "Accepted":
			job = frappe.get_doc("Installation Job", job_name)
			_check_technician(job)
			_set_state(job, "Installed")


# ---------------------------------------------------------------------------
# Sales Invoice
# ---------------------------------------------------------------------------


def sales_invoice_on_submit(doc, method=None):
	job_name = doc.get("custom_installation_job")
	if not job_name:
		return
	job = frappe.get_doc("Installation Job", job_name)
	if not job.sales_invoice:
		_set_job(job, "sales_invoice", doc.name)
	if job.workflow_state == "Installed":
		try:
			_set_state(job, "Completed")
		except Exception:
			frappe.log_error(title=f"Could not complete Installation Job {job.name}")
			frappe.msgprint(
				_("Invoice submitted, but Installation Job {0} could not be moved to Completed. Open it and click Complete.").format(job.name)
			)


@frappe.whitelist()
def create_installation_invoice(job):
	job = frappe.get_doc("Installation Job", job)
	job.check_permission("write")

	if job.workflow_state != "Installed":
		frappe.throw(_("Only installed jobs can be invoiced. This job is {0}.").format(job.workflow_state))
	if job.sales_invoice and frappe.db.exists("Sales Invoice", job.sales_invoice):
		if frappe.db.get_value("Sales Invoice", job.sales_invoice, "docstatus") != 2:
			frappe.throw(_("Sales Invoice {0} already exists for this job.").format(job.sales_invoice))

	sold = {}
	for d in job.devices:
		if d.supply_type == "Sold":
			sold.setdefault(d.item_code, []).append(d.serial_no)

	si = frappe.new_doc("Sales Invoice")
	si.update(
		{
			"customer": job.customer,
			"company": job.company,
			"posting_date": today(),
			"due_date": today(),
			"update_stock": 1 if sold else 0,
			"project": job.project,
			"custom_installation_job": job.name,
			"remarks": _("Installation Job {0}").format(job.name),
		}
	)
	if sold:
		si.set_warehouse = TECH_WH

	used = []
	for c in job.charges:
		if flt(c.rate) <= 0:
			frappe.throw(_("Enter a price for {0} in the Charges table.").format(c.item_code))
		row = {"item_code": c.item_code, "qty": flt(c.qty), "rate": flt(c.rate)}
		if c.description:
			row["description"] = c.description
		if c.item_code in sold:
			serials = sold[c.item_code]
			if flt(c.qty) != len(serials):
				frappe.throw(
					_("Qty for {0} must be {1}, the number of sold {0} devices on this job.").format(
						c.item_code, len(serials)
					)
				)
			row.update({"warehouse": TECH_WH, "use_serial_batch_fields": 1, "serial_no": "\n".join(serials)})
			used.append(c.item_code)
		elif frappe.db.get_value("Item", c.item_code, "is_stock_item"):
			frappe.throw(
				_("{0} is a stock item but no device on this job is Sold as {0}. Bill installation and subscription for Brycomm-owned devices instead.").format(c.item_code)
			)
		si.append("items", row)

	missing = [i for i in sold if i not in used]
	if missing:
		frappe.throw(_("Add a Charges row with the selling price for the sold device(s): {0}").format(", ".join(missing)))
	if not si.items:
		frappe.throw(_("Add the charges for this job before invoicing."))

	if job.sales_person:
		si.append("sales_team", {"sales_person": job.sales_person, "allocated_percentage": 100})
	si.insert()
	_set_job(job, "sales_invoice", si.name)
	return si.name


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def installation_job_query(user=None):
	user = user or frappe.session.user
	if is_technician_only(user):
		return "`tabInstallation Job`.technician = {0}".format(frappe.db.escape(user))
	return ""


def installation_job_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_technician_only(user):
		return doc.technician == user
	return None


def task_query(user=None):
	user = user or frappe.session.user
	if is_technician_only(user):
		return "`tabTask`._assign like {0}".format(frappe.db.escape('%"' + user + '"%'))
	return ""


def task_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if is_technician_only(user):
		try:
			assigned = json.loads(doc.get("_assign") or "[]")
		except (ValueError, TypeError):
			assigned = []
		return user in assigned
	return None


def redirect_technician(login_manager=None):
	"""Send technician-only users straight to Taskist after login."""
	if is_technician_only():
		frappe.local.response["home_page"] = "/taskist"


# ---------------------------------------------------------------------------
# Taskist API (used by the Installation panel in the task detail view)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_installation(task_name):
	frappe.has_permission("Task", doc=task_name, throw=True)
	job = _job_for_task(task_name)
	user = frappe.session.user
	return {
		"name": job.name,
		"state": job.workflow_state,
		"customer": job.customer_name or job.customer,
		"contact_phone": job.contact_phone,
		"location": job.location,
		"installation_date": str(job.installation_date) if job.installation_date else None,
		"technician": job.technician,
		"technician_name": job.technician_name,
		"source_warehouse": job.source_warehouse,
		"accepted_on": str(job.accepted_on) if job.accepted_on else None,
		"installed_on": str(job.installed_on) if job.installed_on else None,
		"technician_notes": job.technician_notes,
		"is_my_job": job.technician == user,
		"devices": [
			{
				"name": d.name,
				"item_code": d.item_code,
				"serial_no": d.serial_no,
				"supply_type": d.supply_type,
				"device_status": d.device_status,
				**{f: d.get(f) for f in TECH_EDITABLE},
			}
			for d in job.devices
		],
	}


@frappe.whitelist()
def accept_installation_receipt(task_name):
	job = _job_for_task(task_name)
	_check_technician(job)
	if job.workflow_state != "Assigned":
		frappe.throw(_("Installation Job {0} is {1}, so receipt cannot be accepted now.").format(job.name, job.workflow_state))
	_set_state(job, "Accepted")
	return get_installation(task_name)


def _apply_device_details(job, devices, notes=None):
	if isinstance(devices, str):
		devices = json.loads(devices or "[]")
	by_name = {d.get("name"): d for d in devices or []}
	for row in job.devices:
		data = by_name.get(row.name)
		if not data:
			continue
		for f in TECH_EDITABLE:
			if f in data:
				row.set(f, (data.get(f) or "").strip() or None)
	if notes is not None:
		job.technician_notes = notes


@frappe.whitelist()
def save_installation_details(task_name, devices, notes=None):
	job = _job_for_task(task_name)
	_check_technician(job)
	if job.workflow_state != "Accepted":
		frappe.throw(_("Vehicle details can only be changed while the job is Accepted."))
	_apply_device_details(job, devices, notes)
	job.flags.ignore_permissions = True
	job.save()
	return get_installation(task_name)


@frappe.whitelist()
def complete_installation(task_name, devices=None, notes=None):
	job = _job_for_task(task_name)
	_check_technician(job)
	if job.workflow_state != "Accepted":
		frappe.throw(_("Installation Job {0} is {1}, so it cannot be marked installed.").format(job.name, job.workflow_state))
	if devices is not None:
		_apply_device_details(job, devices, notes)
	frappe.flags.in_installation_sync = True
	try:
		_set_state(job, "Installed")
	finally:
		frappe.flags.in_installation_sync = False
	return get_installation(task_name)


@frappe.whitelist()
def search_financiers(query="", page_length=20):
	filters = {}
	if query:
		filters["name"] = ["like", f"%{query}%"]
	return frappe.get_all(
		"Tracking Financier", filters=filters, fields=["name"], order_by="name asc", page_length=cint(page_length)
	)
