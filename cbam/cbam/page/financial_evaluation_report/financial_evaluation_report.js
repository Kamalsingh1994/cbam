frappe.pages['financial-evaluation-report'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Financial Evaluation Report'),
		single_column: true,
	});

	// Layout
	$(page.body).html(`
		<div class="container p-0">

			<!-- Group 1 -->
            <div class="row mb-3 align-items-center">
                <div class="col">
                    <div class="section-title mb-2">🧾 Select Article</div>
                    <div class="row gx-2" id="filter-section-group-1"></div>
                </div>
                <div class="col-auto d-flex align-items-center" style="margin-top: 22px;">
                    <button class="btn btn-primary btn-xs clear-selections text-nowrap filter-clear-btn" id="clear-group-1">Clear All</button>
                </div>
            </div>

            <!-- Group 2 -->
            <div class="row mb-4 align-items-center">
                <div class="col">
                    <div class="section-title mb-2">📅 Calculation Based On</div>
                    <div class="row gx-2" id="filter-section-group-2"></div>
                </div>
                <div class="col-auto d-flex align-items-center" style="margin-top: 22px;">
                    <button class="btn btn-primary btn-xs clear-selections text-nowrap filter-clear-btn" id="clear-group-2">Clear All</button>
                </div>
            </div>
			<div class="row mb-4" id="card-section">
				<div class="row gx-3" id="compact-stat-row"></div>
			</div>

			<div class="frappe-card mb-4" id="chart-section"></div>

			<div class="frappe-card mb-4" id="table-scroll-container" style="overflow-x: auto;">
				<div id="table-section"></div>
			</div>
		</div>
	`);

	// Add custom style for stat card width and button alignment
	$(page.body).append(`
		<style>
			.stat-card.frappe-card {
				min-width: 230px;
				max-width: 260px;
			}
			.filter-clear-btn {
				min-width: 70px;
				margin-left: 8px;
			}
			@media (max-width: 991px) {
				.stat-card.frappe-card {
					min-width: 180px;
					max-width: 100%;
				}
			}
		</style>
	`);

	// Filters
	const filters = {
		cn_code: create_filter("CN Code", "MultiSelectList", "cn_code", "#filter-section-group-1"),
		supplier: create_filter("Supplier", "MultiSelectList", "supplier", "#filter-section-group-1"),
		article_number: create_filter("Article Number", "MultiSelectList", "article_number", "#filter-section-group-1"),
		reporting_period: create_filter("Reporting Period", "MultiSelectList", "reporting_period", "#filter-section-group-1"),

        year: create_filter("Year", "Link", "year", "#filter-section-group-2", null, "Year", frappe.datetime.get_today().split("-")[0]),
		ets_price_type: create_filter("ETS Price Type", "Select", "ets_price_type", "#filter-section-group-2", ["", "Actual", "Prediction"]),
		// month: create_filter("Month", "Select", "month", "#filter-section-group-2", moment.months(), null, moment().format('MMMM')),
		ets_price: create_filter("ETS Price", "Select", "ets_price", "#filter-section-group-2")
	};

    // Clear Group 1 Filters
    $('#clear-group-1').on('click', () => {
        ["cn_code", "supplier", "article_number", "reporting_period"].forEach(key => {
            if (filters[key]) {
                filters[key].set_value([]);
            }
        });
        load_report_table();
    });


    // Clear Group 2 Filters
    $('#clear-group-2').on('click', () => {
        ["ets_price_type", "year", "month", "ets_price"].forEach(key => {
            if (filters[key]) {
                if (filters[key].df.fieldtype === "MultiSelectList") {
                    filters[key].set_value([]);
                } else {
                    filters[key].set_value(null);
                }
            }
        });
        load_report_table();
    });

    // Group 1 filter change listener
["cn_code", "supplier", "article_number", "reporting_period"].forEach(key => {
	const ctrl = filters[key];

	if (ctrl) {
		ctrl.df.onchange = () => {
			console.log(`[${key}] changed:`, ctrl.get_value());
			load_report_table(); // 🔄 Refresh table based on updated filters
		};
	}
});


    //Group 2 filter change listener
    ["ets_price_type", "year", "month", "ets_price"].forEach(key => {
        const ctrl = filters[key];
    
        if (ctrl) {
            ctrl.df.onchange = () => {
                const selected_filters = {
                    ets_price_type: filters.ets_price_type.get_value(),
                    year: filters.year.get_value(),
                    // month: filters.month.get_value(),
                    ets_price: filters.ets_price.get_value()
                };
                console.log("Selected Filters:", selected_filters);
                update_stat_card_values(key, selected_filters);

                // 🔄 Refresh ETS Price options dynamically
                if (key === "ets_price_type" || key === "year") {
                    refresh_ets_price_options(
                        filters.ets_price_type.get_value(),
                        filters.year.get_value()
                    );
                }
                load_report_table();
            };
        }
    });

    function get_all_selected_filters() {
        const selected_filters = {};
    
        // Collect Group 1 filters
        ["cn_code", "supplier", "article_number", "reporting_period"].forEach(key => {
            selected_filters[key] = filters[key]?.get_value?.() || [];
        });
    
        // Collect Group 2 filters
        ["ets_price_type", "year", "ets_price"].forEach(key => {
            selected_filters[key] = filters[key]?.get_value?.() || "";
        });
    
        // Get card values from DOM (optional)
        selected_filters.cbam_factor = parseFloat($(`[data-stat="cbam-factor"]`).text()) || 0;
        selected_filters.bench_mark = parseFloat($(`[data-stat="bench-mark-emission-value"]`).text()) || 0;
        selected_filters.emission_value = parseFloat($(`[data-stat="standard-emission-value"]`).text()) || 0;
        selected_filters.ets_price_value = parseFloat($(`[data-stat="ets-price"]`).text()) || 0;
    
        return selected_filters;
    }

    
    function refresh_ets_price_options(ets_price_type, year) {
        if (!ets_price_type || !year) return;
    
        frappe.db.get_list("ETS Carbon Price", {
            fields: ["name", "price", "price_date"],
            filters: {
                ets_price_type: ets_price_type
            },
            limit: 100
        }).then(res => {
            const prices = res
                .filter(row => {
                    const y = frappe.datetime.str_to_obj(row.price_date).getFullYear();
                    return y == year;
                })
                .map(row => row.price);
            
            filters.ets_price.df.options = prices;
            filters.ets_price.refresh();

            // ✅ Set latest price as default
            console.log("Available Prices:", prices);
            if (prices.length) {
                filters.ets_price.set_value(String(prices[0]));
            }
        });
    }

    function update_stat_card_values(key, filters) {
        // 🟢 If ETS Price changed (not year or type), update stat directly without backend call
        if (key === "ets_price") {
            $(`.stat-value[data-stat="ets-price"]`).text(filters.ets_price || 0.0);
            return;
        }

        clear_stats()
        // 🟡 For year or type change, fetch updated values from backend
        frappe.call({
            method: "cbam.cbam.page.financial_evaluation_report.financial_evaluation_report.get_cards_value",
            args: { filters },
            callback: function (r) {
                if (!r.message) return;
                console.log("Stat Card Values:", r.message);
    
                const updated_values = {
                    "standard-emission-value": r.message.emission_value || 0.0,
                    "bench-mark-emission-value": r.message.bench_mark || 0.0,
                    "cbam-factor": r.message.cbam_factor || 0.0,
                    "ets-price": r.message.ets_price || 0.0,
                    "year": filters.year || frappe.datetime.get_today().split("-")[0]
                };
    
                Object.entries(updated_values).forEach(([key, val]) => {
                    $(`.stat-value[data-stat="${key}"]`).text(val);
                });
            }
        });
    }
    
    
    
	function create_filter(label, fieldtype, fieldname, parentSelector, options = null, link_to = null, default_val = null) {
		const df = {
			label,
			fieldname,
			fieldtype,
			options,
			default: default_val
		};
		if (link_to) df.options = link_to;

		// MultiSelectList source logic
		if (fieldtype === "MultiSelectList") {
            df.get_data = function (txt) {
                // Get current values from filters
                const supplier_vals = filters.supplier?.get_value?.() || [];
                const cn_code_vals = filters.cn_code?.get_value?.() || [];
        
                if (fieldname === "article_number") {
                    return frappe.db.get_list("External Good", {
                        fields: ["article_no as value", "article_no as description"],
                        filters: [
                            ["article_no", "like", `%${txt}%`],
                            supplier_vals.length ? ["supplier", "in", supplier_vals] : null,
                            cn_code_vals.length ? ["cn_code", "in", cn_code_vals] : null
                        ].filter(Boolean),
                        distinct: true,
                        limit: 20
                    });
                }
        
                if (fieldname === "reporting_period") {
                    return frappe.db.get_list("External Good", {
                        fields: ["reporting_period as value", "reporting_period as description"],
                        filters: [
                            ["name", "like", `%${txt}%`],
                            supplier_vals.length ? ["supplier", "in", supplier_vals] : null,
                            cn_code_vals.length ? ["cn_code", "in", cn_code_vals] : null
                        ].filter(Boolean),
                        distinct: true,
                        limit: 20
                    });
                }
        
                // Static filters
                if (fieldname === "cn_code") {
                    return frappe.db.get_list("CN Code", {
                        fields: ["cn_code as value", "cn_code as description"],
                        filters: [["cn_code", "like", `%${txt}%`]],
                        limit: 20
                    });
                }
                if (fieldname === "supplier") {
                    return frappe.db.get_list("External Good", {
                        fields: ["supplier as value", "supplier as description"],
                        filters: [["supplier", "like", `%${txt}%`]],
                        distinct: true,
                        limit: 20
                    });
                }
            };
        }

		// Use col for each filter, but let parent be row for alignment
		const $col = $("<div class='col mb-2'></div>").appendTo(parentSelector);

		const control = frappe.ui.form.make_control({
			parent: $col,
			df: df
		});
		control.refresh();
		return control;
	}

    clear_stats()
    function clear_stats(){
        // Stat Cards
        const compact_stats = [
            { label: "Standard Emission Value", value: '--' },
            { label: "Bench Mark Emission Value", value: '--' },
            { label: "CBAM Factor", value: '--' },
            { label: "ETS Price", value: '--' },
            { label: "Year", value: 2025 }
        ];
        
        $('#compact-stat-row').empty();
        
        compact_stats.forEach(stat => {
            $('#compact-stat-row').append(
                `<div class='col mb-2'>${render_compact_card(stat.label, stat.value)}</div>`
            );
        });
    }
	

	// Chart
	let chart = null;
	
	function update_chart(chart_data) {
		// Clear previous chart
		$('#chart-section').empty();
		
		if (!chart_data || !chart_data.labels || chart_data.labels.length === 0) {
			$('#chart-section').html('<div class="text-center text-muted p-4">No data available for chart</div>');
			return;
		}
		
		chart = new frappe.Chart("#chart-section", {
			title: "Standard vs Actual Cost (by Year)",
			data: {
				labels: chart_data.labels,
				datasets: [
					{
						name: "Actual Cost",
						values: chart_data.actual_costs
					},
					{
						name: "Standard Cost",
						values: chart_data.standard_costs
					}
				]
			},
			type: 'bar',
			height: 300,
			barOptions: {
				stacked: false,
				spaceRatio: 0.7
			},
			colors: ['#004080', '#e67300'], // Optional: dark blue & orange
			axisOptions: {
				xAxisMode: 'tick',
				yAxisMode: 'tick',
				showAxes: true
			}
		});
	}

	// Initialize chart with empty data
	update_chart(null);

	// Table
	load_report_table();

	function load_report_table(filters = {}) {

        const selected_filters = get_all_selected_filters();

        console.log("selected_filters on load_report_table", selected_filters)

		frappe.call({
			method: "cbam.cbam.page.financial_evaluation_report.financial_evaluation_report.get_report_data",
			args: { 
                "filters": filters, 
                "selected_filters": selected_filters 
            },
			callback: function (r) {
				if (r.message) {
					const { columns, data, chart_data } = r.message;

					const formattedColumns = [
						...columns.map(col => ({
							id: col.fieldname,
							name: col.label,
							width: col.width || 150,
							resizable: true,
							editable: false
						}))
					];

					// Clear previous table
					$('#table-section').empty();

					new DataTable("#table-section", {
						columns: formattedColumns,
						data: data,
						layout: "fixed",
						stickyHeader: true,
						inlineFilters: true,
						scrollY: "500px",
						scrollX: true,
                        className: "frappe-datatable"
					});
					
					// Update chart with new data
					update_chart(chart_data);
				}
			}
		});
	}

	// Card render
	function render_compact_card(label, value) {
		return `
			<div class="frappe-card d-flex flex-column justify-content-center align-items-center border rounded shadow-sm p-3 text-center stat-card h-100">
				<div class="text-muted small">${label}</div>
				<div class="fw-bold fs-5 mt-1 stat-value" data-stat="${label.toLowerCase().replace(/ /g, '-')}">${value}</div>
			</div>
		`;
	}
};
