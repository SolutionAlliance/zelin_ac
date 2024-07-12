// Copyright (c) 2023, Vnimy and contributors
// For license information, please see license.txt

frappe.ui.form.on('Profit and Loss Statement Settings', {
	refresh: function(frm) {
		if (!frm.doc.items || frm.doc.items.length === 0){
			frm.add_custom_button('导入范例数据', function() {
				frm.events.import_example_data(frm);
			});
		}
	},

	import_example_data(frm) {
		frm.call('get_example_data').then(r => {
			r.message.items.sort((a, b) => a.idx > b.idx ? 1 : -1);
			frm.set_value(r.message);
		});
	},
});
