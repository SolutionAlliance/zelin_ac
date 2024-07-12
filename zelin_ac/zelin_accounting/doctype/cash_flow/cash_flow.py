# Copyright (c) 2023, Vnimy and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Cast_
from frappe.utils import cint, cstr, flt, getdate, datetime, get_first_day, get_last_day, formatdate
from erpnext.accounts.report.trial_balance.trial_balance import get_rootwise_opening_balances


class CashFlow(Document):
    def validate(self):
        self.sync_subtotal()
        self.validate_split_amount()

    def validate_split_amount(self):
        gl_entries = [row.gl_entry for row in self.items]
        if gl_entries:
            gl_entry_amount_list = frappe.get_all('GL Entry', 
                filters = {'name': ('in', gl_entries)},
                fields = ['name', 'debit', 'credit']
            )
            gl_entry_amount_map = {
                row.name: row.debit - row.credit for row in gl_entry_amount_list
            } 
            gl_entry_wise_amount = {}
            for row in self.items:                            
                gl_entry = row.gl_entry
                gl_entry_wise_amount.setdefault(gl_entry, 0)
                gl_entry_wise_amount[gl_entry] += row.debit - row.credit

            for (gl_entry, total_amount) in gl_entry_wise_amount.items():
                gl_entry_amount = gl_entry_amount_map.get(gl_entry, 0)
                if abs(flt(total_amount - gl_entry_amount)) > 0:
                    frappe.throw(_("GL Entry {0} total amount {1} does not match amount {2} in general ledger".format(
                        gl_entry, total_amount, gl_entry_amount
                    )))

    def sync_subtotal(self):
        self.cash_flow_subtotal = []
        cash_flow_codes = frappe.get_all('Cash Flow Code', 
            fields =[
                "code",
                "cash_flow_name",
                "cash_flow_type",                
                "formula",
                "is_outflow"
            ],
            order_by = 'report_sequence')
        code_type_map = {row.code:row.cash_flow_type for row in cash_flow_codes}

        subtotal_by_code_map = {}
        subtotal_by_type_map = {}
        for row in self.items:
            cash_flow_code = row.cash_flow_code
            cash_flow_type = code_type_map.get(cash_flow_code)
            if cash_flow_code:
                subtotal_by_code_map.setdefault(cash_flow_code, 0)
                subtotal_by_code_map[cash_flow_code] += (row.debit or 0) - (row.credit or 0)
                subtotal_by_type_map.setdefault(cash_flow_type, 0)
                subtotal_by_type_map[cash_flow_type] += row.debit - row.credit
        last_month_yearly_amount_map = {}
        if self.month != '1':
            cf = frappe.qb.DocType('Cash Flow')
            cf_subtotal = frappe.qb.DocType('Cash Flow Subtotal')
            last_cf = frappe.qb.from_(cf
                ).where(
                    (cf.company == self.company)
                    & (cf.fiscal_year == self.fiscal_year)
                    & (Cast_(cf.month,'integer') < cint(self.month))
                    & (cf.docstatus == 1)
                ).select(cf.name
                ).orderby(Cast_(cf.month,'integer'), order=frappe.qb.desc
                ).limit(1
                ).run(pluck='name')
            if last_cf:    
                data = frappe.qb.from_(cf_subtotal                
                    ).where(cf_subtotal.parent.isin(last_cf)                    
                    ).select(cf_subtotal.code, cf_subtotal.yearly_amount                
                    ).run(as_list = 1)
                last_month_yearly_amount_map = frappe._dict(data)
        year = frappe.db.get_value('Fiscal Year', self.fiscal_year,'year_start_date').year        
        from_date = get_first_day(datetime.date(
            year=year, month=cint(self.month), day=1))
        year_start_date = get_first_day(datetime.date(
            year=year, month=1, day=1))    
        to_date = get_last_day(datetime.date(
            year=year, month=cint(self.month), day=1))
        filters = frappe._dict({
            'company': self.company,
            'from_date': from_date,
            'to_date': to_date
        })
        opening_balances = get_rootwise_opening_balances(filters, "Balance Sheet")
        #filters.from_date = year_start_date
        #yearly_opening_balances = get_rootwise_opening_balances(filters, "Balance Sheet")
        cash_accounts = frappe.get_all("Account", 
            filters = {"Company": self.company,
                        "account_type": ("in", ['Cash','Bank'])
            },
            pluck = 'name')

        above_subtotal, above_yearly_subtotal = 0, 0
        for row in cash_flow_codes:
            cash_flow_type = code_type_map.get(row.code)
            subtotal_doc = frappe._dict({
                'code': row.code,
                'cash_flow_name': row.cash_flow_name,
                'cash_flow_type': row.cash_flow_type
            })
            
            if not row.formula:
                subtotal_doc.monthly_amount = subtotal_by_code_map.get(row.code, 0)
                above_subtotal += subtotal_doc.monthly_amount
                if row.is_outflow and subtotal_doc.monthly_amount:
                    subtotal_doc.monthly_amount *= -1
            else:
                if row.formula == 'type_subtotal':
                    subtotal_doc.monthly_amount = subtotal_by_type_map.get(cash_flow_type, 0)
                elif row.formula == 'last_period_balance':
                    subtotal_doc.monthly_amount = sum(
                        opening_balances.get(account,{}).get('opening_debit',0) - 
                        opening_balances.get(account,{}).get('opening_credit',0)
                        for account in cash_accounts)
                    above_subtotal += subtotal_doc.monthly_amount
                elif row.formula == 'above_subtotal':
                    subtotal_doc.monthly_amount = above_subtotal
            #本年累计金额
            last_month_yearly_amount = last_month_yearly_amount_map.get(row.code, 0)
            if row.formula == 'last_period_balance':                
                subtotal_doc.yearly_amount = subtotal_doc.monthly_amount if self.month == '1' else last_month_yearly_amount                
            else:
                subtotal_doc.yearly_amount = last_month_yearly_amount + (subtotal_doc.monthly_amount or 0)

            self.append('cash_flow_subtotal', subtotal_doc)        

    @frappe.whitelist()
    def get_cash_flow_items(self):
        year = frappe.db.get_value('Fiscal Year', self.fiscal_year,'year_start_date').year
        from_date = get_first_day(datetime.date(
            year=year, month=cint(self.month), day=1))
        to_date = get_last_day(datetime.date(
            year=year, month=cint(self.month), day=1))
        account = frappe.qb.DocType('Account')    
        gle = frappe.qb.DocType('GL Entry')
        pe = frappe.qb.DocType('Payment Entry')
        data = frappe.qb.from_(gle
            ).join(account
            ).on( (gle.account == account.name) & (gle.company == account.company)
            ).left_join(pe
            ).on((gle.voucher_type == 'Payment Entry') & (gle.voucher_no == pe.name)
            ).where(
                (account.company == self.company) &
                (gle.is_cancelled == 0) &
                (gle.posting_date >= from_date) &
                (gle.posting_date <= to_date) &
                (account.account_type.isin(['Cash','Bank']))
            ).select(
                gle.name.as_('gl_entry'),
                gle.posting_date,                
                gle.account,
                pe.party_type,
                pe.party,
                gle.cost_center,
                gle.debit,
                gle.credit,                
                gle.against,
                gle.voucher_type,
                gle.voucher_no,                
                gle.project,
                gle.remarks
            ).run(as_dict = True)

        existing_code_map = {}    
        if self.items:            
            existing_code_map = {row.gl_entry:row.cash_flow_code for row in self.items if row.cash_flow_code}
            self.items = []    
        for d in data:
            d.against = d.against[:140] #修改了字段类型为Data,避免出现超140字符的情况
            d.cash_flow_code = existing_code_map.get(d.gl_entry)
            self.append('items', d)
        
        self.assign_default_cash_flow_code(existing_code_map = existing_code_map)

    def assign_default_cash_flow_code(self, existing_code_map = {}):
        accounts = {row.account for row in self.items}
        accounts.update({row.against for row in self.items if row.against})
        account_cf_map = frappe._dict(frappe.get_all(
            'Account', 
            filters = {'name': ('in', accounts),
                        'cash_flow_code': ('is', 'set')
            },
            fields = ['name', 'cash_flow_code'],
            as_list = 1
        ))
        party_type_cf_map = frappe._dict(frappe.get_all(
            'Cash Flow Code',
            filters = {
                'party_type':('is', 'set')
            },
            fields = ['party_type','name'],
            as_list = 1
        ))
        party_by_party_type = {} #{'Customer':{'customer1','customer2'}}
        for row in self.items:
            if row.party_type and row.party_type in ('Customer', 'Supplier'):
                party_by_party_type.setdefault(row.party_type, set()).add(row.party)
        party_cf_map = {}
        for (party_type, parties) in party_by_party_type.items():
            party_cf_map.update(
                frappe._dict(frappe.get_all(
                    party_type, 
                    filters = {'name': ('in', parties),
                                'cash_flow_code': ('is', 'set')
                    },
                    fields = ['name', 'cash_flow_code'],
                    as_list = 1
                ))
            )
        if account_cf_map or party_type_cf_map or party_cf_map:
            for row in self.items:
                if row.gl_entry not in existing_code_map:
                    cash_flow_code = (account_cf_map.get(row.account) or account_cf_map.get(row.against)
                        or party_cf_map.get(row.party) or party_type_cf_map.get(row.party_type)
                    )
                    if cash_flow_code:
                        row.cash_flow_code = cash_flow_code