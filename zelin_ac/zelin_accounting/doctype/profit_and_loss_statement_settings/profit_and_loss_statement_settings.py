# Copyright (c) 2023, Vnimy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

import os

class ProfitandLossStatementSettings(Document):
	@frappe.whitelist()
	def get_example_data(self):
		return frappe.get_file_json(os.path.join(os.path.dirname(__file__), "example_data.json"))
