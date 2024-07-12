# Copyright (c) 2023, 杨嘉祥 and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, getdate, datetime, get_first_day, get_last_day, formatdate, nowdate
from erpnext.accounts.utils import FiscalYearError,get_fiscal_year,get_currency_precision


def execute(filters=None):
  validate_filters(filters)
  columns = get_columns(filters)

  settings = frappe.get_single("Profit and Loss Statement Settings")
  fields = ['idx','label','indent','calc_type','calc_sources','amount_from']
  #globals().update(locals())
  data = [frappe._dict({f:d.get(f) for f in fields}) for d in settings.items]      
  data = get_data(data, filters)

  return columns, data

def validate_filters(filters):
  if not filters.fiscal_year:
    frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

  fiscal_year = frappe.db.get_value(
      "Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"], as_dict=True
  )
  if not fiscal_year:
    frappe.throw(
        _("Fiscal Year {0} does not exist").format(filters.fiscal_year))
  else:
    filters.year_start_date = getdate(fiscal_year.year_start_date)
    filters.year_end_date = getdate(fiscal_year.year_end_date)

  if filters.month:
    year = frappe.db.get_value('Fiscal Year', fiscal_year,'year_start_date').year
    filters.from_date = get_first_day(datetime.date(
        year=year, month=cint(filters.month), day=1))
    filters.to_date = get_last_day(datetime.date(
        year=year, month=cint(filters.month), day=1))
  else:
    filters.from_date = filters.year_start_date
    filters.to_date = filters.year_end_date

  filters.from_date = getdate(filters.from_date)
  filters.to_date = getdate(filters.to_date)

  if filters.from_date > filters.to_date:
    frappe.throw(_("From Date cannot be greater than To Date"))

  if (filters.from_date < filters.year_start_date) or (filters.from_date > filters.year_end_date):
    frappe.msgprint(
        _("From Date should be within the Fiscal Year. Assuming From Date = {0}").format(
            formatdate(filters.year_start_date)
        )
    )

    filters.from_date = filters.year_start_date

  if (filters.to_date < filters.year_start_date) or (filters.to_date > filters.year_end_date):
    frappe.msgprint(
        _("To Date should be within the Fiscal Year. Assuming To Date = {0}").format(
            formatdate(filters.year_end_date)
        )
    )
    filters.to_date = filters.year_end_date

def get_acc_nums(filters, data):
  """
    # source: -5001,5051=>  {acc_nums:[5001,5051], minus_factor:[-1,1]}
  """
  accounts = frappe.get_all('Account', 
    fields = ['account_number','lft','rgt','is_group','parent_account', 'root_type'],
    filters = {
      'company': filters.company
      #'root_type': ('in',('Income', 'Expense'))
    }
  )
  account_number_map = {acc.account_number:acc for acc in accounts}

  acc_nums = []
  for d in data:
    if d.calc_type and d.calc_sources and d.calc_type == "Closing Balance":       
      splitted_nums = list(filter(None, d.calc_sources.split(",")))
      #globals().update(locals())
      d.acc_nums = [f[1:] if f and f[0] == '-' else f for f in splitted_nums]
      d.minus_factor = [-1 if f and f[0] == '-' else 1 for f in splitted_nums]
      acc_nums.extend(d.acc_nums)
      d.accounts = [account_number_map.get(acc_num) for acc_num in d.acc_nums]

  parent_children_map = {}
  non_group_acc_nums = []
  for acc_num in acc_nums:
    account = account_number_map.get(acc_num)
    if account and account.is_group:
      child_account_nums = [acc.account_number for acc in accounts
         if acc.is_group == 0 and acc.lft > account.lft and acc.rgt < account.rgt]
      parent_children_map[acc_num] = child_account_nums
      non_group_acc_nums.extend(child_account_nums)
    else:
      non_group_acc_nums.append(acc_num)

  return non_group_acc_nums, parent_children_map

def get_data(data, filters):
  """
  1. 获取利润表设置明细中计算方式为期末余额的科目号清单
    1.1 获取每个父科目号的下层记账科目号清单
    1.2 剔除科目号负号前缀
  2. 获取当月以及年初到当月底记帐科目会计凭证小计金额  
  3. 获取利润表设置明细行计算方式为期末余额的汇总金额
     3.1 获取记账科目小计
     3.2 获取父科目小计（下层记账科目汇总)
     3.3 处理科目号负号前缀
     3.4 收入科目自动*-1
  4. 获取利润表设置明细行计算方式为计算公式的汇总金额  
  """

  def get_amount(amount_map, acc_num, amount_from=None):
    return amount_map.get(acc_num, {}).get(amount_from or 'balance', 0)

  acc_nums, parent_children_map = get_acc_nums(filters, data)
  monthly_amount_map = get_balance_on(company=filters.company, date=filters.to_date, 
    start_date = filters.from_date,account_numbers = acc_nums)
  if filters.year_start_date == filters.from_date:
    month_end_amount_map = monthly_amount_map
  else:
    month_end_amount_map = get_balance_on(company=filters.company, date=filters.to_date,
      start_date = filters.year_start_date,account_numbers = acc_nums)
  rows_map = {}
  for d in data:
    d.amount, d.month_end_amount = 0, 0
    if d.calc_type and d.calc_sources and d.calc_type == "Closing Balance":
      row_monthly_amount, row_month_end_amount = 0, 0
      for (i,account) in enumerate(d.accounts):
        if not account: continue
        acc_num = account.account_number
        minus_factor = d.minus_factor[i]
        children = parent_children_map.get(acc_num)
        monthly_amount, month_end_amount = 0, 0
        if not account.is_group:        
          monthly_amount = get_amount(monthly_amount_map, acc_num, d.amount_from) * minus_factor
          month_end_amount = get_amount(month_end_amount_map, acc_num, d.amount_from) * minus_factor
        elif children:
          for child in children:
            monthly_amount += get_amount(monthly_amount_map,child, d.amount_from) * minus_factor
            month_end_amount += get_amount(month_end_amount_map, child, d.amount_from) * minus_factor
        if account.root_type == "Income":
          monthly_amount *= -1
          month_end_amount *= -1
        row_monthly_amount += monthly_amount
        row_month_end_amount += month_end_amount
      d.amount = row_monthly_amount
      d.month_end_amount = row_month_end_amount

    rows_map[cstr(d.idx)]= {          
        "amount": d.amount,
        "month_end_amount": d.month_end_amount
    }     

  for d in data:
    if d.calc_type and d.calc_sources and d.calc_type == "Calculate Rows":
      splitted_rows = list(filter(None, d.calc_sources.split(",")))
      #globals().update(locals())
      d.acc_nums = [f[1:] if f and f[0] == '-' else f for f in splitted_rows]
      d.minus_factor = [-1 if f and f[0] == '-' else 1 for f in splitted_rows]      
      monthly_amount, month_end_amount = 0, 0
      for (i, row_num) in enumerate(d.acc_nums):
        minus_factor = d.minus_factor[i]        
        row = rows_map.get(cstr(row_num))
        monthly_amount += row.get("amount", 0.0) * minus_factor
        print(i, row_num, monthly_amount)
        month_end_amount += row.get("month_end_amount", 0.0) * minus_factor
      d.amount = monthly_amount
      d.month_end_amount = month_end_amount  
      rows_map[cstr(d.idx)] = {          
          "amount": d.amount,
          "month_end_amount": d.month_end_amount
      }

  return data

def get_columns(filters):
  columns = [
      {
          "label": "项目",
          "fieldname": "label",
          "fieldtype": "Data",
          "width": 300,
      },
      {
          "label": "行次",
          "fieldname": "idx",
          "fieldtype": "Int",
          "width": 60,
      },
      {
          "label": "金额",
          "fieldname": "amount",
          "fieldtype": "Currency",
          "width": 120,
      }
  ]

  if filters.month:
    columns.extend([
        {
            "label": "月底累计数",
            "fieldname": "month_end_amount",
            "fieldtype": "Currency",
            "width": 120,
        }
    ])

  return columns

@frappe.whitelist()
def get_balance_on(
  account=None,
  date=None,
  party_type=None,
  party=None,
  company=None,
  in_account_currency=False,
  cost_center=None,
  ignore_account_permission=True,
  account_type=None,
  start_date=None,
  account_numbers=[],
  with_period_closing_entry=None,
  debug = False
):
  """
  基于 from erpnext.accounts.utils import get_balance_on
  增加了
    with_period_closing_entry
    account_numbers
  ignore_account_permission 默认为True
  返回
  {科目编号：{credit: 1, debit:2, balance:1}}
  字典而不是一个金额数字
  """

  if not account and frappe.form_dict.get("account"):
    account = frappe.form_dict.get("account")
  if not date and frappe.form_dict.get("date"):
    date = frappe.form_dict.get("date")
  if not party_type and frappe.form_dict.get("party_type"):
    party_type = frappe.form_dict.get("party_type")
  if not party and frappe.form_dict.get("party"):
    party = frappe.form_dict.get("party")
  if not cost_center and frappe.form_dict.get("cost_center"):
    cost_center = frappe.form_dict.get("cost_center")

  cond = ["is_cancelled=0"]
  if not with_period_closing_entry:
    cond.append('voucher_type != "Period Closing Voucher"')

  if start_date:
    cond.append("posting_date >= %s" % frappe.db.escape(cstr(start_date)))
  if date:
    cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
  else:
    # get balance of all entries that exist
    date = nowdate()

  if account:
    acc = frappe.get_doc("Account", account)

  try:
    year_start_date = get_fiscal_year(date, company=company, verbose=0)[1]
  except FiscalYearError:
    if getdate(date) > getdate(nowdate()):
      # if fiscal year not found and the date is greater than today
      # get fiscal year for today's date and its corresponding year start date
      year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
    else:
      # this indicates that it is a date older than any existing fiscal year.
      # hence, assuming balance as 0.0
      return 0.0

  if account:
    report_type = acc.report_type
  else:
    report_type = ""

  if cost_center and report_type == "Profit and Loss":
    cc = frappe.get_doc("Cost Center", cost_center)
    if cc.is_group:
      cond.append(
        """ exists (
        select 1 from `tabCost Center` cc where cc.name = gle.cost_center
        and cc.lft >= %s and cc.rgt <= %s
      )"""
        % (cc.lft, cc.rgt)
      )

    else:
      cond.append("""gle.cost_center = %s """ % (frappe.db.escape(cost_center, percent=False),))

  if account:
    if not (frappe.flags.ignore_account_permission or ignore_account_permission):
      acc.check_permission("read")

    # different filter for group and ledger - improved performance
    if acc.is_group:
      cond.append(
        """exists (
        select name from `tabAccount` ac where ac.name = gle.account
        and ac.lft >= %s and ac.rgt <= %s
      )"""
        % (acc.lft, acc.rgt)
      )

      # If group and currency same as company,
      # always return balance based on debit and credit in company currency
      if acc.account_currency == frappe.get_cached_value("Company", acc.company, "default_currency"):
        in_account_currency = False
    else:
      cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False),))

  if account_type:
    accounts = frappe.db.get_all(
      "Account",
      filters={"company": company, "account_type": account_type, "is_group": 0},
      pluck="name",
      order_by="lft",
    )

    cond.append(
      """
      gle.account in (%s)
    """
      % (", ".join([frappe.db.escape(account) for account in accounts]))
    )

  if party_type and party:
    cond.append(
      """gle.party_type = %s and gle.party = %s """
      % (frappe.db.escape(party_type), frappe.db.escape(party, percent=False))
    )

  if company:
    cond.append("""gle.company = %s """ % (frappe.db.escape(company, percent=False)))

  if account_numbers or account or (party_type and party) or account_type:
    precision = get_currency_precision()
    if in_account_currency:
      select_field = (
        "sum(round(debit_in_account_currency, %s)) - sum(round(credit_in_account_currency, %s))"
      )
    else:
      select_field = "sum(round(debit, %s)) - sum(round(credit, %s))"
  join_str = ""
  if account_numbers:
    join_str =" INNER JOIN `tabAccount` acct on gle.account = acct.name"
    select_field = "acct.account_number, sum(round(debit, %s)), sum(round(credit, %s)) "
    cond.append(
        """
        account_number in (%s)
      """
        % (", ".join([frappe.db.escape(account_number) for account_number in account_numbers]))
      )
    group_by = " group by acct.account_number "
  else:
    group_by = ""
  bal = frappe.db.sql(
    """
    SELECT {0}
    FROM `tabGL Entry` gle
    {1}
    WHERE {2}
    {3}
    """.format(
      select_field, join_str, " and ".join(cond), group_by
    ),
    (precision, precision),
    debug = debug
  )
  # if bal is None, return 0
  if bal:
    result = frappe._dict({
      b[0]:{'Debit':b[1],
         'Credit': b[2],
         'Balance': b[1] - b[2]
      }
      for b in bal
    })
  return result if bal else {}


"""
for testing
from zelin_ac.zelin_accounting.report.fin_profit_and_loss_statement.fin_profit_and_loss_statement import *
filters = frappe._dict({"company":"则霖信息技术（深圳）有限公司","fiscal_year":"2024","month":"2"})
validate_filters(filters)
columns = get_columns(filters)
settings = frappe.get_single("Profit and Loss Statement Settings")
fields = ['idx','label','indent','calc_type','calc_sources','amount_from']
globals().update(locals())
data = [frappe._dict({f:d.get(f) for f in fields}) for d in settings.items]   
data = get_data(data, filters)
"""