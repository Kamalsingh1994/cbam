from frappe import _

def get_data():
	return {
		"fieldname": "report_id",
		"transactions": [
			{
				"label": _("External Good"), 
				"items": ["External Good"]
			}
		],
	}
