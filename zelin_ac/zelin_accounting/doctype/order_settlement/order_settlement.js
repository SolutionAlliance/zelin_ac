// Copyright (c) 2023, Vnimy and contributors
// For license information, please see license.txt

frappe.ui.form.on('Order Settlement', {
	onload: function(frm) {        
		if (frm.is_new()){
			const fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
			fiscal_year && frm.set_value('fiscal_year', fiscal_year);
			const date = new Date();
			const month = date.getMonth() + 1;
			frm.set_value('month', month);
		}
	},
	refresh(frm){
		if (frm.doc.docstatus !== 0){
			frm.add_custom_button(__('Repost Item Valuation'), () => {
				const vouchers = frm.doc.items.map(
					r=>{return r.stock_entry}
				)
				frappe.set_route('List', 'Repost Item Valuation', 
					{
						company: frm.doc.company,
						//creation: ['>', frm.doc.modified],
						//生成的成本调整凭证记账日期是入库单的记账日期，
						//posting_date: frm.doc.modified.split(' ')[0],
						voucher_type:'Stock Entry',					
						voucher_no: ['in', vouchers]});
			}, __('View'));
		}
	},	
	get_items(frm) {
		frappe.call({
			method: "get_items",
			doc: frm.doc,
			callback: function(r) {
				refresh_field("items");
				refresh_field("expenses");
				frm.dirty();
			}
		});
	},
});

frappe.ui.form.on('Order Settlement Item', {
    qty(frm, cdt, cdn) {
        calculate_subtotal(frm)  
    },
    items_add(frm, cdt, cdn) {
        calculate_subtotal(frm)  
    },
    items_delete(frm, cdt, cdn) {
        calculate_subtotal(frm)  
    }
})

frappe.ui.form.on('Order Settlement Expense', {
    actual_expense(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
		row.allocatable_expense = row.actual_expense - (row.included_expense | 0);
		row.variance = row.allocatable_expense - (row.allocated_expense | 0);
		frm.refresh_field('expenses'); 
    },
	included_expense(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
		row.allocatable_expense = row.actual_expense - (row.included_expense | 0);
		row.variance = row.allocatable_expense - (row.allocated_expense | 0);
		frm.refresh_field('expenses'); 
    },
    variance(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
		row.allocatable_expense = row.variance  + (row.allocated_expense | 0)
		row.actual_expense = row.allocatable_expense + (row.included_expense | 0)
		frm.refresh_field('expenses'); 
    }
})


var calculate_subtotal = function(frm){                    //字段值变更后触发这段代码执行
	let ws_included_expense = frm.doc.items.reduce((accumulator, currentValue) => {  
		// 如果当前Workstation已经存在于累加器中，则增加其included_expense  
		let workstation = currentValue.workstation? currentValue.workstation: "empty"
		if (accumulator[workstation]) {  
		  accumulator[workstation] += currentValue.included_expense;  
		} else {  
		  // 否则，在累加器中创建一个新的条目，并设置qty  
		  accumulator[workstation] = currentValue.included_expense;  
		}  
		return accumulator;  
	  }, {});
	frm.doc.expenses.forEach(
		row=>{
			let workstation = row.workstation? row.workstation: "empty";
			frappe.model.set_value(row.doctype, row.name, 'included_expense', ws_included_expense[workstation] | 0)
		}
	)
    frm.refresh_field('expenses');              //刷新主表字段，显示更新后结果
}