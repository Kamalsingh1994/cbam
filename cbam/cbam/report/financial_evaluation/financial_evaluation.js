// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Evaluation"] = {
	onload: function (report) {
		const style = document.createElement('style');
		style.innerHTML = `
		  .dt-instance-1 .dt-cell__content--col-0 {
			width: auto !important;
		  }
		`;
		document.head.appendChild(style);
	},	  
	filters: [
	  {
		fieldname: "cn_code",
		label: __("CN Code"),
		fieldtype: "MultiSelectList",
		get_data(txt) {
		  return frappe.db.get_list("CN Code", {
			fields: ["cn_code as value", "cn_code as description"],
			filters: [["cn_code", "like", `%${txt}%`]],
			limit: 20
		  });
		}
	  },
	  {
		fieldname: "supplier",
		label: __("Supplier"),
		fieldtype: "MultiSelectList",
		get_data(txt) {
		  return frappe.db.get_list("Good", {
			fields: ["supplier_name as value", "supplier_number as description"],
			filters: [["supplier_name", "like", `%${txt}%`]],
			distinct: true,
			limit: 20
		  });
		}
	  },
	  {
		fieldname: "article_number",
		label: __("Article Number"),
		fieldtype: "MultiSelectList",
		get_data(txt) {
		  return frappe.db.get_list("Good", {
			fields: ["article_number as value" , "article_number as description"],
			filters: [["article_number", "like", `%${txt}%`]],
			distinct: true,
			limit: 20
		  });
		}
	  },
	  {
		fieldname: "reporting_period",
		label: __("Reporting Period"),
		fieldtype: "MultiSelectList",
		get_data(txt) {
		  return frappe.db.get_list("Customs Import", {
			fields: ["name as value" , "name as description"],
			filters: [["name", "like", `%${txt}%`]],
			distinct: true,
			limit: 20
		  });
		}
	  }
	]
  };
  
