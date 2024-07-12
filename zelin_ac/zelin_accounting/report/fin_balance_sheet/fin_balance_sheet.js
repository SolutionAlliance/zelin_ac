// Copyright (c) 2023, 杨嘉祥 and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Fin Balance Sheet"] = $.extend(
	{},
	erpnext.financial_statements
);


frappe.query_reports["Fin Balance Sheet"] = {
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
		},
		{
			"fieldname": "month",
			"label": "月份",
			"fieldtype": "Select",
			"options": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
			"default": new Date().getMonth() + 1,
			"depends_on": "eval: !doc.show_all_months",
		},
		{
			"fieldname": "show_all_months",
			"label": "显示所有月份",
			"fieldtype": "Check",
			"default": 0,
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) {
			return value;
		}

		// 将所有负数变为正数，并且为货币格式
		if (column.fieldname.endsWith('_balance')) {
			if (data[column.fieldname] < 0) {
				value = Math.abs(data[column.fieldname]);
				value = format_currency(value, data.currency);
				// 右对齐
				column.align = 'right';
			}
		}

		const prefix = column.fieldname.slice(0, 4);
		if (['lft_', 'rgt_'].includes(prefix) && data[prefix + 'empty']) {
			value = '';
		} else if (data.empty) {
			value = '';
		}

		if (column.fieldname.endsWith('_balance')) {
			if (!data[prefix + 'calc_type']) {
				value = '';
			}
		}

		if (column.fieldname.startsWith('balance_')) {
			if (!data.calc_type) {
				value = '';
			}
		}

		if (column.fieldname === 'lft_name' && data.lft_indent > 0) {
			value = `<span style="padding-left: ${data.lft_indent * 20}px;">${value}</span>`;
		}

		if (column.fieldname === 'rgt_name' && data.rgt_indent > 0) {
			value = `<span style="padding-left: ${data.rgt_indent * 20}px;">${value}</span>`;
		}

		if (column.fieldname.startsWith('lft_')) {
			if (data.lft_bold && value) {
				value = `<span style="font-weight:bold;">${value}</span>`;
			}
		} else if (column.fieldname.startsWith('rgt_')) {
			if (data.rgt_bold && value) {
				value = `<span style="font-weight:bold;">${value}</span>`;
			}
		} else {
			if (data.bold && value) {
				value = `<span style="font-weight:bold;">${value}</span>`;
			}
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
	}
}