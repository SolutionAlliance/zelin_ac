frappe.ui.form.on('Cash Flow', {
	setup: function(frm) {
		frm.set_query("cash_flow_code", function(doc) {			
			return {			
				filters: {
					'formula': ['is', 'not set'],					
				}
			}
		});
	}
})