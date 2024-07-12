import frappe


def stock_entry_validate(doc, method):
    set_masterial_issue_expense_account(doc)
    set_manufacture_production_cost_account(doc)

def subcontracting_receipt_validate(doc, method):
    # 14版委外入库明细行还没有采购订单明细字段
    if not hasattr(doc.items[0], 'purchase_order_item'):
        return
    account_map = frappe._dict(frappe.get_all("Purchase Order Item",
        filters = {'name': ('in', 
            {row.purchase_order_item for row in doc.items if row.purchase_order_item})
        },
        fields = ['name', 'expense_account'],
        as_list = 1
    ))
    if account_map:
        for row in doc.items:
            expense_account = account_map.get(row.purchase_order_item)
            if expense_account:
                row.expense_account = expense_account

def set_masterial_issue_expense_account(doc):
    if doc.stock_entry_type in ['Material Issue', 'Material Receipt'] and doc.reason_code:
        expense_account = doc.expense_account
        if not expense_account:
            expense_account = frappe.db.get_value('Material Issue Default Account',
                {'company': doc.company,
                 'parent': doc.reason_code
                },
                'expense_account'
            )
        if expense_account:
            for row in doc.items:
                row.expense_account = expense_account

def set_manufacture_production_cost_account(doc):
    if doc.stock_entry_type == 'Manufacture':
        production_input_account, production_output_account = frappe.db.get_value('Company',
            doc.company, ['production_input_account', 'production_output_account'])
        if production_input_account or production_output_account:
            for row in doc.items:
                if row.is_finished_item and production_output_account:
                    row.expense_account = production_output_account
                elif row.s_warehouse and production_input_account:
                    row.expense_account = production_input_account