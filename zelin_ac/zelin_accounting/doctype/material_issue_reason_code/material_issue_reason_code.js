// Copyright (c) 2023, Vnimy and contributors
// For license information, please see license.txt

frappe.ui.form.on('Material Issue Reason Code', {
	setup: function (frm) {
		frm.set_query('expense_account', 'accounts', function (doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					'company': d.company,
					'account_type': "Expense Account",
					"is_group": 0
				}
			}
		});
	}
	// refresh: function(frm) {

	// }
});
