from . import __version__ as app_version

app_name = "zelin_ac"
app_title = "Zelin Accounting"
app_publisher = "Vnimy"
app_description = "Zelin Accounting"
app_email = "vnimy@mediad.cn"
app_license = "MIT"

fixtures = [
    {
        "doctype": "Cash Flow Code",
        "filters": [
        ]
    }
]

doctype_js = {
	"Stock Entry" : "public/js/stock_entry.js",
	"Account" : "public/js/account.js"		
}

doc_events = {
 	"Stock Entry": {
 		"validate": "zelin_ac.doc_events.stock_entry_validate"
	},
	"Subcontracting Receipt": {
 		"validate": "zelin_ac.doc_events.subcontracting_receipt_validate"
	}
}

override_doctype_class = {
	"Purchase Invoice": "zelin_ac.overrides.CustomPurchaseInvoice",
	"Sales Invoice": "zelin_ac.overrides.CustomSalesInvoice"
}