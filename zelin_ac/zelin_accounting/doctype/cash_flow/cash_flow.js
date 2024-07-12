// Copyright (c) 2023, Vnimy and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cash Flow', {
	setup: function(frm) {
		frm.set_query("cash_flow_code", "items", function(doc, cdt, cdn) {
			const child = locals[cdt][cdn];
			const is_outflow = child.debit? 0 : 1;			
			return {			
				filters: {
					formula: ['is', 'not set'],
					is_outflow: is_outflow
				}
			}
		});
	},
	refresh: function(frm) {
        frm.add_custom_button(__('Download Cash Flow'), function() {
           download_cash_flow(frm);
        });
    },
	onload: function(frm) {        
		if (frm.is_new()){
			const fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
			fiscal_year && frm.set_value('fiscal_year', fiscal_year);
			const date = new Date();
			const month = date.getMonth() + 1;
			frm.set_value('month', month);
		}
	},
	get_cash_flow_items(frm) {
		frappe.call({
			method: "get_cash_flow_items",
			doc: frm.doc,
			callback: function(r) {
				refresh_field("items");
				frm.dirty();
			}
		});
	},
});

frappe.ui.form.on('Cash Flow Item', {
	cash_flow_code(frm, cdt, cdn){
		const child = locals[cdt][cdn];
		const cf_code = child.cash_flow_code;
		frm.grids[0].grid.get_selected_children().forEach( (row) =>{
				if (row.name !== child.name && !row.cash_flow_code){
					frappe.model.set_value(row.doctype, row.name, 'cash_flow_code', cf_code);
				}
			}
		)
	}
})
var download_cash_flow = function(frm) {
	var data = [];
	var docfields = [];
	data.push([]);
	$.each(frappe.get_meta("Cash Flow Subtotal").fields, (i, df) => {
		// don't include the read-only field in the template
		if (frappe.model.is_value_type(df.fieldtype)) {
			data[0].push(__(df.label));			
			docfields.push(df);
		}
	});
	// add data
	$.each(frm.doc.cash_flow_subtotal || [], (i, d) => {
		var row = [];
		$.each(docfields, (i, df) => {
			var value = d[df.fieldname];			
			if (df.fieldtype === "Date" && value) {
				value = frappe.datetime.str_to_user(value);
			}
			row.push(value || "");
		});
		data.push(row);
	});
	frappe.tools.downloadify(data, null, __("Cash Flow Report"));
}