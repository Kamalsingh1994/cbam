// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Evaluation"] = {
	// onload: function (report) {
	// 	const style = document.createElement('style');
	// 	style.innerHTML = `
	// 	  .dt-instance-1 .dt-cell__content--col-0 {
	// 		width: auto !important;
	// 	  }
	// 	`;
	// 	document.head.appendChild(style);

	// 	const style1= document.createElement('style');
	// 	document.head.appendChild(style1);
	// },	
	onload: function (report) {
		const style = document.createElement("style");
		style.innerHTML = `
			/* Always allow scroll + space for Clear All */
			ul.dropdown-menu.show {
				max-height: 220px !important;
				overflow-y: auto !important;
				padding-bottom: 8px; /* fallback padding */
			}

			/* Optional: Ensure smooth rendering of items */
			ul.dropdown-menu.show .selectable-items {
				margin-bottom: 32px; /* space below list so button doesn't overlap */
			}
	
			/* Clear All button placement */
			ul.dropdown-menu.show > li.text-right {
				/* only stick if dropdown scrolls */
				position: relative;
				bottom: auto;
				background: white;
				padding: 6px 12px;
				border-top: 1px solid #f0f0f0;
			}
	
			/* If you want it sticky only when needed */
			ul.dropdown-menu.show.scrollable > li.text-right {
				position: sticky;
				bottom: -10px;
				box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
			}
		`;
		document.head.appendChild(style);
	
		// Add 'scrollable' class dynamically if content overflows
		new MutationObserver(() => {
			document.querySelectorAll("ul.dropdown-menu.show").forEach(ul => {
				const isScrollable = ul.scrollHeight > ul.clientHeight;
				ul.classList.toggle("scrollable", isScrollable);
			});
		}).observe(document.body, { childList: true, subtree: true });


		frappe.call({
			method: "cbam.cbam.report.financial_evaluation.financial_evaluation.get_ets_prices",  // use your actual path
			callback: function(r) {
			  frappe.after_ajax(() => {
				if (r.message && r.message.length) {
				  const options = r.message.map(row => row.price.toString());
				  const filter = frappe.query_report.get_filter('ets_price');
		
				  if (filter) {
					filter.df.options = options;
					filter.refresh();
		
					// Optional: set default value
					frappe.query_report.set_filter_value('ets_price', options[0]);
				  } else {
					console.warn("Filter 'ets_price' not found");
				  }
				} else {
				  console.warn("No ETS prices returned from backend");
				}
			  });
			}
		});
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
	  },
	  {
		fieldname: "ets_price",
		label: __("ETS Price"),
		fieldtype: "Select",
		options: [], // dynamically populated
		reqd: 0
	  }
	]
  };
  
