frappe.ui.form.on('Stock Entry', {
    setup: function (frm) {
		frm.set_query('expense_account', function (doc) {			
			return {
				filters: {
					'company': doc.company,
					'account_type': "Expense Account",
					"is_group": 0
				}
			}
		});
	},
    reason_code(frm){
        if (frm.doc.reason_code){
            let filters = {'parent': frm.doc.reason_code,
                'company': frm.doc.company    
            }            
            frappe.call({
                method: "frappe.client.get_value",
    			args: {
    				doctype: "Material Issue Default Account",
    				filters: filters,
    				fieldname:"expense_account",
    				parent:"Material Issue Reason Code"
    			},
            })
            .then(r=>{
                if (!r.exc){
                    frm.set_value('expense_account', r.message.expense_account);
                }
            })
        }
        else {
            frm.set_value('expense_account', "")
        }  
    }
})