import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center


class CustomPurchaseInvoice(PurchaseInvoice):
    def get_gl_entries(self, warehouse_account=None):
        """
        在系统自动计算的税额与税票税额有差异时，允许手工输入实际税额，
        此代码将系统基于标准税额生成的总帐凭证税科目分录调整为手工税额
        将税额差异调至公司主数据中的圆整差异科目
        """

        gl_entries = super(CustomPurchaseInvoice, self).get_gl_entries(warehouse_account = warehouse_account)
        add_tax_adjust_gl_entries(self, gl_entries)
        return gl_entries

class CustomSalesInvoice(SalesInvoice):
    def get_gl_entries(self, warehouse_account=None):

        gl_entries = super(CustomSalesInvoice, self).get_gl_entries(warehouse_account = warehouse_account)
        add_tax_adjust_gl_entries(self, gl_entries)
        return gl_entries

def add_tax_adjust_gl_entries(doc, gl_entries):
        
        tax_amount_map = {} #按税科目小计手工输入的实际税额
        total_adjust_amount = 0
        for row in doc.taxes:
            if row.charge_type != 'Actual' and row.actual_tax_amount and flt(row.actual_tax_amount - row.tax_amount):
                tax_account = row.account_head                
                tax_amount_map.setdefault(tax_account, 0)
                tax_amount_map[tax_account] += row.actual_tax_amount

        if tax_amount_map:
            for (tax_account, actual_tax_amount) in tax_amount_map.items():
                for row in gl_entries:
                    if row.account == tax_account:
                        if row.debit:
                            row.debit = actual_tax_amount
                            row.debit_in_account_currency = actual_tax_amount
                            total_adjust_amount +=  actual_tax_amount - row.debit
                        else:
                            row.credit = actual_tax_amount
                            row.credit_in_account_currency = actual_tax_amount
                            total_adjust_amount += actual_tax_amount - row.credit
                        break            
            add_adjust_gl_entry(doc, gl_entries, total_adjust_amount * -1)
                    
        return gl_entries

def add_adjust_gl_entry(doc, gl_entries, adjust_amount):
    """"""
    round_off_account, round_off_cost_center = get_round_off_account_and_cost_center(
        doc.company, "Purchase Invoice", doc.name, doc.use_company_roundoff_cost_center
    )
    has_round_off_account = False
    for row in gl_entries:
        if row.account == round_off_account:
            if row.debit:
                row.debit += adjust_amount
                row.debit_in_account_currency += adjust_amount                
            else:
                row.credit += adjust_amount                            
                row.credit_in_account_currency += adjust_amount                
            has_round_off_account = True
            break
    if not has_round_off_account:
        gl_entries.append(
            doc.get_gl_dict(
                {
                    "account": round_off_account,
                    "against": None,
                    "debit_in_account_currency": adjust_amount,
                    "debit": adjust_amount,
                    "cost_center": round_off_cost_center
                    if doc.use_company_roundoff_cost_center
                    else (doc.cost_center or round_off_cost_center),
                }            
            )
        )