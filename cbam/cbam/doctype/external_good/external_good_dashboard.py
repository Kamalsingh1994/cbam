from frappe import _

def get_data():
	return {
		"fieldname": "external_good",
		"transactions": [
			{
				"label": _("CBAM Report Data"), 
				"items": ["CBAM Report"]
			}
		],
	}
