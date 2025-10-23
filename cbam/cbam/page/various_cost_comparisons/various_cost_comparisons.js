// Copyright (c) 2024, CBAM Team. All rights reserved.
// MIT License. See license.txt

/**
 * Financial Evaluation Report Page
 * Optimized and refactored for Frappe best practices and maintainability.
 */

frappe.provide('cbam.pages');

let missingDataPopupShown = false; // <--- GLOBAL. Do not redeclare in any function!

frappe.pages['various-cost-comparisons'].on_page_load = function(wrapper) {
    if (!sessionStorage.getItem('various_cost_comparisons_reloaded')) {
        sessionStorage.setItem('various_cost_comparisons_reloaded', '1');
        location.reload();
        return;
    } else {
        sessionStorage.removeItem('various_cost_comparisons_reloaded');
    }
    (function () {
        const page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __('Financial Dashboard'),
            single_column: true,
        });

        // Layout
        render_layout(page.body);
        cbam.inject_custom_styles(page.body);

        // Filters
        const filters = setup_filters();
        cbam.setup_filter_clear_buttons(filters, load_report_table);
        cbam.setup_filter_listeners(filters, load_report_table, update_stat_card_values, (ets_price_type, year) => cbam.refresh_ets_price_options(filters, ets_price_type, year));

        // Setup Year-ETS Price Type logic
        setupYearEtsPriceTypeLogic(filters);

        // Pagination state
        let start = 0;
        let page_length = 50;
        let total_count = 0;
        let all_data = [];
        let datatable = null;

        // Initial Stats, Chart, and Table
        clear_stats();
        // cbam.update_chart(null);
        load_report_table(true);

        // Helper: Get table data, optionally per tonne
        function get_table_data(data, per_tonne = false) {
            return data.map(row => {
                let real_emission_cost, standard_emission_cost;
                if (!per_tonne) {
                    real_emission_cost = Number(row.real_emission_cost) || 0;
                    standard_emission_cost = Number(row.standard_emission_cost) || 0;
                } else {
                    let mass_tonnes = Number(row.raw_mass_tonne) || 0;
                    if (mass_tonnes > 0) {
                        real_emission_cost = (Number(row.real_emission_cost) || 0) / mass_tonnes;
                        standard_emission_cost = (Number(row.standard_emission_cost) || 0) / mass_tonnes;
                    } else {
                        real_emission_cost = 0;
                        standard_emission_cost = 0;
                    }
                }
                
                // Convert units for display
                const cbam_benchmark = Number(row.cbam_benchmark) || 0;
                const standard_emission_factor = Number(row.standard_emission_factor) || 0;
                const real_emission_value = Number(row.real_emission_value) || 0;
                
                return {
                    ...row,
                    cbam_benchmark: cbam_benchmark.toFixed(3),
                    standard_emission_factor: standard_emission_factor.toFixed(3),
                    real_emission_value: real_emission_value.toFixed(3),
                    real_emission_cost: real_emission_cost.toFixed(3),
                    standard_emission_cost: standard_emission_cost.toFixed(3)
                };
            });
        }

        // --- Show Selected Rows Toggle Logic ---
        function get_selected_rows_data() {
            if (!datatable) return [];
            const selectedIndexes = datatable.rowmanager.getCheckedRows();
            return selectedIndexes.map(idx => all_data[idx]);
        }

        // Listen for 'Show Cost per tonne' toggle event
        $('#table-toggle').on('change', function() {
            const per_tonne = $(this).is(':checked');
            // Update table
            const table_data = get_table_data(all_data, per_tonne);
            if (datatable) {
                datatable.refresh(table_data);
            }
            // Update chart (respect 'Show Selected rows' toggle)
            const showSelected = $('#selected-rows-toggle').is(':checked');
            let chart_data;
            if (showSelected) {
                const selectedData = get_selected_rows_data();
                chart_data = cbam.get_chart_data(selectedData, per_tonne);
            } else {
                chart_data = cbam.get_chart_data(all_data, per_tonne);
            }
            cbam.update_chart(chart_data);
        });

        // Listen for 'Show Selected rows' toggle event
        $('#selected-rows-toggle').on('change', function() {
            const showSelected = $(this).is(':checked');
            const per_tonne = $('#table-toggle').is(':checked');
            let chart_data;
            if (showSelected) {
                const selectedData = get_selected_rows_data();
                chart_data = cbam.get_chart_data(selectedData, per_tonne);
            } else {
                chart_data = cbam.get_chart_data(all_data, per_tonne);
            }
            cbam.update_chart(chart_data);
        });

        // Update chart live when selection changes if 'Show Selected rows' is ON
        function bind_datatable_selection_events() {
            if (!datatable) return;
            datatable.on('onCheckRow', function() {
                update_export_button_state();
                if ($('#selected-rows-toggle').is(':checked')) {
                    const selectedData = get_selected_rows_data();
                    const per_tonne = $('#table-toggle').is(':checked');
                    cbam.update_chart(cbam.get_chart_data(selectedData, per_tonne));
                }
            });
            datatable.on('onUncheckRow', function() {
                if ($('#selected-rows-toggle').is(':checked')) {
                    const selectedData = get_selected_rows_data();
                    const per_tonne = $('#table-toggle').is(':checked');
                    cbam.update_chart(cbam.get_chart_data(selectedData, per_tonne));
                }
            });
        }

        function update_export_button_state() {
            const selected = datatable?.rowmanager?.getCheckedRows?.() || [];
            $('#export').prop('disabled', selected.length === 0);
        }

        /**
         * Setup Year-ETS Price Type field logic
         */
        function setupYearEtsPriceTypeLogic(filters) {
            // Wait for page to fully load
            setTimeout(() => {
                // Find the year and ETS price type fields
                const yearField = $('label:contains("Year")').closest('.form-group').find('select');
                const etsPriceTypeField = $('label:contains("ETS Price Basis")').closest('.form-group').find('select');
                
                if (yearField.length > 0 && etsPriceTypeField.length > 0) {
                    // Populate ETS Price Type options
                    const etsOptions = ['', 'Spot Price', 'Future (Dec)'];
                    
                    // Update the ETS Price Type field options
                    etsPriceTypeField.empty();
                    etsOptions.forEach(option => {
                        if (option === '') {
                            etsPriceTypeField.append('<option value=""></option>');
                        } else {
                            etsPriceTypeField.append(`<option value="${option}">${option}</option>`);
                        }
                    });
                    
                    // Set default value to Spot Price
                    etsPriceTypeField.val('Spot Price');
                    
                    // Add change event listener to year field
                    yearField.on('change', function() {
                        const selectedYear = parseInt($(this).val());
                        const currentYear = new Date().getFullYear();
                        

                        
                        if (selectedYear && selectedYear > currentYear) {
                            // Future year: set ETS Price Type to Future (Dec) and make read-only
                            etsPriceTypeField.val('Future (Dec)');
                            etsPriceTypeField.prop('disabled', true);
                        } else if (selectedYear && selectedYear == currentYear) {
                            // Current year: make ETS Price Type editable and set to Spot Price
                            etsPriceTypeField.prop('disabled', false);
                            etsPriceTypeField.val('Spot Price');
                        } else {
                            // Past year: make ETS Price Type editable and set to Spot Price
                            etsPriceTypeField.prop('disabled', false);
                            etsPriceTypeField.val('Spot Price');
                        }
                        
                        // Trigger filter change to update ETS Price
                        if (selectedYear) {
                            const selectedEtsType = etsPriceTypeField.val();

                            if (selectedEtsType) {
                                // Manually trigger the filter change to update ETS Price
                                cbam.refresh_ets_price_options(filters, selectedEtsType, selectedYear);
                            }
                        }
                    });
                    
                    // Add change event listener to ETS Price Type field
                    etsPriceTypeField.on('change', function() {
                        const selectedEtsType = $(this).val();

                        
                        // Ensure Year field is never read-only
                        yearField.prop('disabled', false);
                        yearField.prop('readonly', false);
                        
                        // Update ETS Price when ETS Price Type changes
                        const selectedYear = parseInt(yearField.val());

                        if (selectedYear && selectedEtsType) {
                            // Manually trigger the filter change to update ETS Price
                            cbam.refresh_ets_price_options(filters, selectedEtsType, selectedYear);
                        }
                    });
                    
                    // Apply initial logic
                    yearField.trigger('change');
                }
            }, 1000);
        }


        /**
         * Render the main page layout.
         * @param {HTMLElement} body
         */
        function render_layout(body) {
            $(body).html(`
                <div class="container p-0">
                    <div class="row mb-4 align-items-center">
                        <div class="col">
                            <div class="section-title mb-2">📅 Calculation Based On</div>
                            <div class="row gx-0 align-items-center">
                                <div class="col-6" id="filter-section-group-2"></div>
                                <div class="col-4" id="compact-stat-row"></div>
                            </div>
                        </div>
                        <div class="col-auto d-flex align-items-center" style="margin-top: 22px;">
                            <button class="btn btn-primary btn-xs clear-selections text-nowrap filter-clear-btn" id="clear-group-2">Clear All</button>
                        </div>
                    </div>
                    <div class="frappe-card mb-4" id="chart-section"></div>
                    <!-- Select Article filter section -->
                    <div class="row mb-3 align-items-center">
                        <div class="col">
                            <div class="section-title mb-2">🧾 Select Article</div>
                            <div class="row gx-2" id="filter-section-group-1"></div>
                        </div>
                        <div class="col-auto d-flex align-items-center" style="margin-top: 22px;">
                            <button class="btn btn-primary btn-xs clear-selections text-nowrap filter-clear-btn" id="clear-group-1">Clear All</button>
                        </div>
                    </div>
                    
                    
                    <div class="frappe-card mb-4" id="table-toggle-section">
                        <div class="p-2 d-flex align-items-center gap-5">
                            <span class="ms-2 small">Show Cost per tonne of Product</span>&nbsp;
                            <label class="switch-compact mb-0 me-4 ms-2">
                                <input type="checkbox" id="table-toggle">
                                <span class="slider-compact round"></span>
                            </label>
                            <span class="vr mx-3"></span>
                            <span class="ms-2 small">Show Selected Items Only</span>&nbsp;
                            <label class="switch-compact mb-0 ms-2">
                                <input type="checkbox" id="selected-rows-toggle">
                                <span class="slider-compact round"></span>
                            </label>
                        </div>
                    </div>
                    
                    <!-- Disclaimer Section -->
                    <div class="mb-3 p-3" style="padding: 10px 0px 0px 0px !important;">
                        <div class="alert alert-info mb-0" role="alert">
                            <i class="fa fa-info-circle me-2"></i>
                            <strong>Disclaimer:</strong> You can sort the list by any column and choose which entries to show for comparison.
                        </div>
                    </div>

                    <div class="frappe-card mb-4" id="table-scroll-container" style="overflow-x: auto;">
                        <div id="table-section"></div>
                    </div>
                </div>
            `);
        }

        /**
         * Setup all filters and return the filter controls object.
         * @returns {Object}
         */
        function setup_filters() {
            const currentYear = frappe.datetime.get_today().split('-')[0];
            const filters = {
                cn_code: cbam.create_filter('CN Code', 'MultiSelectList', 'cn_code', '#filter-section-group-1', []),
                supplier: cbam.create_filter('Supplier', 'MultiSelectList', 'supplier', '#filter-section-group-1', []),
                article_number: cbam.create_filter('Article Number', 'MultiSelectList', 'article_number', '#filter-section-group-1', []),
                reporting_period: cbam.create_filter('Reporting Period', 'MultiSelectList', 'reporting_period', '#filter-section-group-1', []),
                year: cbam.create_filter('Year', 'Select', 'year', '#filter-section-group-2', [], null, currentYear),
                ets_price_type: cbam.create_filter('ETS Price Basis', 'Select', 'ets_price_type', '#filter-section-group-2', ['', 'Spot Price', 'Future (Dec)'], null, 'Spot Price'),
            };

            // Populate year filter with available years from ETS Carbon Price
            populate_year_filter(filters.year);

            // CN Code: no dependencies
            filters.cn_code.df.get_data = function(txt) {
                return frappe.db.get_list('CN Code', {
                    fields: ['cn_code as value', 'cn_code as description'],
                    filters: [['cn_code', 'like', `%${txt}%`]],
                    limit: 20,
                });
            };

            // Helper to fetch filter options from backend
            function fetch_filter_options({ txt, filter_type, cn_code = [], supplier = [] }) {
                return frappe.call({
                    method: "cbam.cbam.page.various_cost_comparisons.various_cost_comparisons.get_filter_options",
                    args: {
                        txt,
                        filter_type,
                        cn_code: cn_code.join(","),
                        supplier: supplier.join(",")
                    }
                }).then(r => r.message || []);
            }

            filters.supplier.df.get_data = function(txt) {
                const cn_code = filters.cn_code?.get_value?.() || [];
                return fetch_filter_options({ txt, filter_type: "supplier", cn_code });
            };

            filters.article_number.df.get_data = function(txt) {
                const supplier = filters.supplier?.get_value?.() || [];
                const cn_code = filters.cn_code?.get_value?.() || [];
                return fetch_filter_options({ txt, filter_type: "article_number", supplier, cn_code });
            };

            filters.reporting_period.df.get_data = function(txt) {
                const supplier = filters.supplier?.get_value?.() || [];
                const cn_code = filters.cn_code?.get_value?.() || [];
                return fetch_filter_options({ txt, filter_type: "reporting_period", supplier, cn_code });
            };

            return filters;
        }

        /**
         * Populate the year filter with available years from ETS Carbon Price table
         * @param {Object} yearFilter - The year filter control
         */
        function populate_year_filter(yearFilter) {
            frappe.call({
                method: 'cbam.cbam.page.various_cost_comparisons.various_cost_comparisons.get_available_years',
                callback: function(r) {

                    if (r.message && r.message.length > 0) {
                        // Set the options for the Select field
                        yearFilter.df.options = r.message;
                        
                        // Refresh the filter
                        yearFilter.refresh();
                        
                        // Set default value to current year if available, otherwise first available year
                        const currentYear = frappe.datetime.get_today().split('-')[0];
                        const availableYears = r.message;
                        
                        if (availableYears.includes(currentYear)) {
                            yearFilter.set_value(currentYear);
                        } else if (availableYears.length > 0) {
                            yearFilter.set_value(availableYears[0]);
                        }
                    } else {

                        // Fallback to current year
                        const currentYear = frappe.datetime.get_today().split('-')[0];
                        yearFilter.df.options = [currentYear];
                        yearFilter.refresh();
                        yearFilter.set_value(currentYear);
                    }
                },
                error: function(err) {
                    console.error('Error fetching available years:', err);
                    // Fallback to current year
                    const currentYear = frappe.datetime.get_today().split('-')[0];
                    yearFilter.df.options = [currentYear];
                    yearFilter.refresh();
                    yearFilter.set_value(currentYear);
                }
            });
        }

        /**
         * Update stat card values based on filter changes.
         * @param {string} key
         * @param {Object} filters
         */
        function update_stat_card_values(key, filters) {
            if (key === 'ets_price') {
                const etsPriceValue = filters.ets_price || 0.0;
                const displayValue = etsPriceValue !== 0.0 ? `€${parseFloat(etsPriceValue).toFixed(2)}` : '€0.00';
                $('.stat-value[data-stat="ets-price"]').text(displayValue);
                // After updating ETS Price, reload table and chart with new value
                load_report_table(true, filters);
                return;
            }
            
            clear_stats();
            frappe.call({
                method: 'cbam.cbam.page.various_cost_comparisons.various_cost_comparisons.get_cards_value',
                args: { filters },
                callback: function (r) {
                    if (!r.message) return;
                    
                    const updated_values = {
                        'cbam-factor': r.message.cbam_factor || 0.0,
                        'ets-price': r.message.ets_price || 0.0,
                    };
                    
                    Object.entries(updated_values).forEach(([key, val]) => {
                        let displayValue = val;
                        
                        // Special formatting for CBAM Factor - convert to percentage with 1 decimal place
                        if (key === 'cbam-factor' && val !== 0.0 && val !== null && val !== undefined) {
                            const numValue = parseFloat(val);
                            if (!isNaN(numValue)) {
                                displayValue = (numValue * 100).toFixed(1) + '%';
                                // Store original value in data attribute for calculations
                                $(`.stat-value[data-stat="${key}"]`).attr('data-original-value', val);
                            }
                        }
                        
                        // Special formatting for ETS Price - add Euro symbol with 2 decimal places
                        if (key === 'ets-price' && val !== 0.0 && val !== null && val !== undefined) {
                            displayValue = `€${parseFloat(val).toFixed(2)}`;
                        }
                        
                        $(`.stat-value[data-stat="${key}"]`).text(displayValue);
                    });
                    
                    // After updating stat cards, reload table and chart with new values
                    load_report_table(true, filters);
                },
                error: function () {
                    clear_stats();
                }
            });
        }
        /** 
         * Clear and render stat cards with default values.
         */
        function clear_stats() {
            // Check if stat cards already exist to prevent duplication
            if ($('#compact-stat-row .stat-card').length > 0) {
                return;
            }
            
            const compact_stats = [
                { label: 'CBAM Factor', value: '--' },
                { label: 'ETS Price', value: '€--', display_label: 'EUA Price [€/t CO2]' },
            ];
            $('#compact-stat-row').empty();
            compact_stats.forEach(stat => {
                const displayLabel = stat.display_label || stat.label;
                $('#compact-stat-row').append(`<div class='me-2'>${render_compact_card_with_data_stat(displayLabel, stat.value, stat.label)}</div>`);
            });

        }

        /**
         * Load and render the report table and update chart.
         * @param {boolean} reset If true, reset table and start from first page.
         * @param {Object} [filters={}]
         */
        function load_report_table(reset = false, filters_arg = {}) {
            if (reset) {
                start = 0;
                all_data = [];
                if (datatable) {
                    datatable.destroy();
                    datatable = null;
                }
                missingDataPopupShown = false; // Only reset on full table reset
            }
            const selected_filters = cbam.get_all_selected_filters(filters);
            frappe.call({
                method: 'cbam.cbam.page.various_cost_comparisons.various_cost_comparisons.get_report_data',
                args: { filters: filters_arg, selected_filters, start, page_length },
                callback: function (r) {
                    if (r.message) {
                        const { columns, data, chart_data, total_count: count } = r.message;
                        total_count = count || 0;
                        if (reset) {
                            all_data = data || [];
                        } else {
                            all_data = all_data.concat(data || []);
                        }
                        const formattedColumns = columns.map(col => ({
                            id: col.fieldname,
                            name: col.label,
                            width: col.width || 150,
                            resizable: true,
                            editable: false
                        }));
                        const per_tonne = $('#table-toggle').is(':checked');
                        const table_data = get_table_data(all_data, per_tonne);
                        // Highlight rows with missing_data_reason
                        const missingRows = [];
                        table_data.forEach((row, i) => {
                          if (row.missing_data_reason) {
                            missingRows.push({idx: i, ...row});
                          }
                        });
                        if (!datatable) {
                            $('#table-section').empty();
                            datatable = new DataTable('#table-section', {
                                columns: formattedColumns,
                                data: table_data,
                                layout: 'fixed',
                                stickyHeader: true,
                                inlineFilters: true,
                                scrollY: '500px',
                                scrollX: true,
                                className: 'frappe-datatable',
                                checkboxColumn: true,
                                rowClass: function(row) {
                                  return row.missing_data_reason ? 'missing-data-row' : '';
                                }
                            });
                            bind_datatable_selection_events();
                        } else {
                            datatable.refresh(table_data);
                        }
                        
                        // Update chart (respect 'Show Selected rows' toggle)
                        const showSelected = $('#selected-rows-toggle').is(':checked');
                        let chart_data_final;
                        if (showSelected) {
                            const selectedData = get_selected_rows_data();
                            chart_data_final = cbam.get_chart_data(selectedData, per_tonne);
                        } else {
                            chart_data_final = cbam.get_chart_data(all_data, per_tonne);
                        }
                       
                        setTimeout(() => cbam.update_chart(chart_data_final), 100);
                        render_pagination_controls();
                    }
                },
                error: function () {
                    $('#table-section').empty().html('<div class="text-center text-muted p-4">Failed to load data</div>');
                    cbam.update_chart(null);
                    render_pagination_controls();
                }
            });
        }

        /**
         * Render pagination controls below the table.
         */
        function render_pagination_controls() {
            $('#pagination-controls').remove();
            const showing_from = total_count === 0 ? 0 : 1;
            const showing_to = all_data.length;
            const html = `
                <div id="pagination-controls" class="cbam-pagination-footer d-flex flex-wrap align-items-center justify-content-between mt-2">
                    <div class="d-flex align-items-center gap-2 flex-wrap">
                        <span class="mx-2">${__("Showing")} <b>${showing_from}&ndash;${showing_to}</b> ${__("of")} <b>${total_count}</b></span>
                        <span class="mx-2">| ${__("Rows per load")}: </span>
                        <select id="page-length-select" class="form-select form-select-sm d-inline-block w-auto">
                            <option value="20">20</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                            <option value="500">500</option>
                        </select>
                    </div>
                    <div class="ms-auto">
                        <button id="load-more" class="btn btn-primary btn-sm px-2" ${(all_data.length >= total_count) ? 'disabled' : ''}>${__("Load More")}</button>
                        <button id="export" class="btn btn-primary btn-sm px-2" disabled>${__("Export CSV")}</button>
                    </div>
                </div>
                <style>
                .cbam-pagination-footer {
                    border: 1px solid #e3e6eb;
                    background: #f8f9fa;
                    border-radius: 0.5rem;
                    padding: 0.75rem 1rem;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
                }
                @media (max-width: 600px) {
                    .cbam-pagination-footer { flex-direction: column; align-items: stretch; }
                    .cbam-pagination-footer .ms-auto { margin-left: 0 !important; margin-top: 0.5rem; }
                }
                </style>
            `;
            $('#table-section').after(html);
            $('#page-length-select').val(page_length);
            $('#page-length-select').on('change', function () {
                page_length = parseInt($(this).val(), 10);
                load_report_table(true); // reset and reload
            });
            $('#load-more').on('click', () => {
                start = all_data.length;
                load_report_table(false);
            });
        }

        // Export selected rows to CSV
        $(document).on("click", "#export", function () {
            const selectedRows = get_selected_rows_data();
            if (selectedRows.length === 0) return;

            const csvHeaders = Object.keys(selectedRows[0]);
            const csvRows = selectedRows.map(row => csvHeaders.map(key => `"${(row[key] || "").toString().replace(/"/g, '""')}"`));
            const csvContent = [csvHeaders.join(","), ...csvRows.map(r => r.join(","))].join("\n");

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", "various_cost_comparisons.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });

        /**
         * Render a compact stat card with separate display label and data-stat label.
         * @param {string} displayLabel - The label to display
         * @param {string|number} value - The value to display
         * @param {string} dataStatLabel - The label to use for data-stat attribute
         * @returns {string}
         */
        function render_compact_card_with_data_stat(displayLabel, value, dataStatLabel) {
            return `
                <div class="frappe-card d-flex flex-row justify-content-between align-items-center border rounded p-2 text-start stat-card h-100">
                    <div class="text-muted small mb-0">${displayLabel}</div>
                    <div class="fw-bold fs-6 ms-2 stat-value" data-stat="${dataStatLabel.toLowerCase().replace(/ /g, '-')}">${value}</div>
                </div>
            `;
        }

        // Insert tab navigation just below the page title
        $(page.body).prepend(`
            <ul class="nav nav-tabs mb-3" id="dashboard-tabs">
                <!-- <li class="nav-item">
                    <a class="nav-link" href="/app/ets-price-dashboard">ETS Price Dashboard</a>
                </li> -->  
                <li class="nav-item">
                    <a class="nav-link" href="/app/financial-exposure-forecast">Financial Exposure Forecast</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link active" href="/app/various-cost-comparisons">Various Cost Comparisons</a>
                </li>
            </ul>
        `);

        // Add custom style for active tab background color (black) and bold font
        $(`<style>
          #dashboard-tabs .nav-link.active {
            background-color: #000 !important;
            color: #fff !important;
            border-color: #000 #000 #fff !important;
            font-weight: 600 !important;
          }
          #dashboard-tabs .nav-link {
            color: #000;
            font-weight: 500;
          }
          
          /* Compact stat card styles - matching filter height and inline with filters */
          .stat-card {
            min-width: 120px;
            width: 140px;
            max-width: 140px;
            height: 38px !important;
            transition: all 0.2s ease;
            border: 1px solid #d1d5db;
            background: #fff;
            display: inline-block;
            vertical-align: top;
          }
          
          .stat-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            border-color: #9ca3af;
          }
          
          .stat-card .text-muted {
            font-size: 0.7rem;
            line-height: 1.2;
            color: #6b7280;
          }
          
          .stat-card .stat-value {
            font-size: 0.875rem !important;
            line-height: 1.2;
            white-space: nowrap;
            color: #111827;
          }
          
          /* Ensure filters and stat cards are properly aligned */
          #filter-section-group-2 {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            justify-content: flex-start;
            width: 100%;
          }
          
          #compact-stat-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            justify-content: flex-end;
            width: 100%;
          }
          
          /* Ensure filters have consistent width using filter.js column classes */
          #filter-section-group-2 .form-control,
          #filter-section-group-2 .frappe-control {
            min-width: 140px;
            width: 100%;
            max-width: 160px;
          }
          
          /* Year filter should be slightly wider */
          #filter-section-group-2 .form-control[data-fieldname="year"] {
            min-width: 140px;
            width: 100%;
            max-width: 150px;
          }
          
          /* ETS Price Type filter should be wider for the text */
          #filter-section-group-2 .form-control[data-fieldname="ets_price_type"] {
            min-width: 160px;
            width: 100%;
            max-width: 170px;
          }
          
          /* Responsive adjustments */
          @media (max-width: 768px) {
            .stat-card {
              min-width: 160px;
              max-width: 200px;
              height: 36px !important;
            }
            
            .stat-card .text-muted {
              font-size: 0.65rem;
            }
            
            .stat-card .stat-value {
              font-size: 0.8rem !important;
            }
            
            #filter-section-group-2,
            #compact-stat-row {
              flex-wrap: wrap;
              gap: 0.15rem;
            }
            
            /* Maintain filter widths on mobile */
            #filter-section-group-2 .form-control,
            #filter-section-group-2 .frappe-control {
              min-width: 140px;
              width: 100%;
              max-width: none;
            }
            
            #filter-section-group-2 .form-control[data-fieldname="year"] {
              min-width: 140px;
              width: 100%;
              max-width: none;
            }
            
            #filter-section-group-2 .form-control[data-fieldname="ets_price_type"] {
              min-width: 140px;
              width: 100%;
              max-width: none;
            }
          }
        </style>`).appendTo('head');
    })();
    
};
