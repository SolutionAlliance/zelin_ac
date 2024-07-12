// Copyright (c) 2023, 杨嘉祥 and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Fin Profit and Loss Statement"] = $.extend(
	{},
	erpnext.financial_statements
);


frappe.query_reports["Fin Profit and Loss Statement"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"default": erpnext.utils.get_fiscal_year(frappe.datetime.get_today()),
			"reqd": 1,
			"on_change": function (query_report) {
			}
		},
		{
			"fieldname": "month",
			"label": "月份",
			"fieldtype": "Select",
			"options": ["", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
			"default": new Date().getMonth() + 1,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) {
			return value;
		}

		if (column.fieldname === 'label' && data.indent > 0) {
			value = `<span style="padding-left: ${data.indent * 20}px;">${value}</span>`;
		}

		return value;
	},
	onload: function(report) {

		const views_menu = report.page.add_custom_button_group(__('Financial Statements'));

		report.page.add_custom_menu_item(views_menu, __("Fin Balance Sheet"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Fin Balance Sheet', {company: filters.company});
		});

		report.page.add_custom_menu_item(views_menu, __("Fin Profit and Loss Statement"), function() {
			var filters = report.get_values();
			frappe.set_route('query-report', 'Fin Profit and Loss Statement', {company: filters.company});
		});
	},
	set_breadcrumb() {
		if (!this.report_doc || this.report_doc.ref_doctype) return;
		const ref_doctype = frappe.get_meta(this.report_doc.ref_doctype);
		frappe.breadcrumbs.add(ref_doctype.module);
	}
}