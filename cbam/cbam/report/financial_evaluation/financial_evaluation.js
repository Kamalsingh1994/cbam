// Copyright (c) 2025, phamos GmbH and contributors
// For license information, please see license.txt


frappe.query_reports["Financial Evaluation"] = {
	onload: function () {

		["month", "year", "ets_price_type"].forEach(fieldname => {
			const field = frappe.query_report.get_filter(fieldname);
			if (field) {
				field.df.onchange = updateETSPriceOptions;
				field.refresh();
			}
		});
		
		//ETS price fetch on load
		updateETSPriceOptions();

		// Setup onchange ETS Price Type filter
		const ets_price_type_filter = frappe.query_report.get_filter("ets_price_type");
		if (ets_price_type_filter) {
			ets_price_type_filter.df.onchange = function () {
				const val = frappe.query_report.get_filter_value("ets_price_type");
				const show = val === "Actual" || val === "Prediction";

				// Show/hide from_date and to_date
				frappe.query_report.toggle_filter_display("from_date", !show);
				frappe.query_report.toggle_filter_display("to_date", !show);

				// Clear if hidden
				if (!show) {
					frappe.query_report.set_filter_value("from_date", "");
					frappe.query_report.set_filter_value("to_date", "");
				}

				// Fetch price options
				updateETSPriceOptions();
			};

			ets_price_type_filter.refresh(); // Rebind the updated config
		}

		// ✅ Also bind onchange to from_date and to_date
		["from_date", "to_date"].forEach(fieldname => {
			const field = frappe.query_report.get_filter(fieldname);
			if (field) {
				field.df.onchange = updateETSPriceOptions;
				field.refresh();
			}
		});



		// Preserve existing Clear All style fix
		const style = document.createElement("style");
		style.innerHTML = `
			ul.dropdown-menu.show {
				max-height: 220px !important;
				overflow-y: auto !important;
				padding-bottom: 8px;
			}

			ul.dropdown-menu.show .selectable-items {
				margin-bottom: 32px;
			}

			ul.dropdown-menu.show > li.text-right {
				position: relative;
				bottom: auto;
				background: white;
				padding: 6px 12px;
				border-top: 1px solid #f0f0f0;
			}

			ul.dropdown-menu.show.scrollable > li.text-right {
				position: sticky;
				bottom: -10px;
				box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
			}
		`;
		document.head.appendChild(style);

		new MutationObserver(() => {
			document.querySelectorAll("ul.dropdown-menu.show").forEach(ul => {
				const isScrollable = ul.scrollHeight > ul.clientHeight;
				ul.classList.toggle("scrollable", isScrollable);
			});
		}).observe(document.body, { childList: true, subtree: true });
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
					fields: ["article_number as value", "article_number as description"],
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
					fields: ["name as value", "name as description"],
					filters: [["name", "like", `%${txt}%`]],
					distinct: true,
					limit: 20
				});
			}
		},
		{
			fieldname: "ets_price_type",
			label: __("ETS Price Type"),
			fieldtype: "Select",
			options: ["", "Spot Price", "Future (Dec)"],
			default: "Spot Price"
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Link",
			options: "Year",
			default: frappe.datetime.get_today().split("-")[0]
		},	
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: [
				"January", "February", "March", "April", "May", "June",
				"July", "August", "September", "October", "November", "December"
			],
			default: frappe.datetime.str_to_obj(frappe.datetime.get_today()).toLocaleString('default', { month: 'long' })
		},
		{
			fieldname: "ets_price",
			label: "ETS Price",
			fieldtype: "Select",
			options: [],
			reqd: 0
		}
	]
};

function updateETSPriceOptions() {
	const price_type = frappe.query_report.get_filter_value("ets_price_type");
	const month = frappe.query_report.get_filter_value("month");
	const year = frappe.query_report.get_filter_value("year");

	frappe.call({
		method: "cbam.cbam.report.financial_evaluation.financial_evaluation.get_ets_prices",
		args: {
			price_type,
			month,
			year
		},
		callback: function(r) {
			frappe.after_ajax(() => {
				const filter = frappe.query_report.get_filter('ets_price');
				if (r.message && r.message.length > 0) {
					// const options = r.message.map(row => row.price.toString());
					const options = r.message.map(row => ({
						label: `${row.price} (${frappe.datetime.str_to_user(row.price_date)})`,
						value: row.price.toString()
					}));

					if (filter) {
						filter.df.options = options;
						filter.refresh();

						// frappe.query_report.set_filter_value('ets_price', options[0]);
						if (options.length > 0) {
							frappe.query_report.set_filter_value("ets_price", options[0].value);
						}
						
					} else {
						console.log("Filter 'ets_price' not found");
					}
				} else {
					filter.df.options = [];
					filter.refresh();
					frappe.query_report.set_filter_value('ets_price', []);
					console.log("No ETS prices returned from backend");
				}
			});
		}
	});
}

