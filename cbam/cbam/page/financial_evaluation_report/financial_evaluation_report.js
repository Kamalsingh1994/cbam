// Copyright (c) 2024, CBAM Team. All rights reserved.
// MIT License. See license.txt

/**
 * Financial Evaluation Report Page
 * Optimized and refactored for Frappe best practices and maintainability.
 */

frappe.provide('cbam.pages');

frappe.pages['financial-evaluation-report'].on_page_load = function (wrapper) {
    (function () {
        const page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __('Financial Evaluation Report'),
            single_column: true,
        });

        // Layout
        render_layout(page.body);
        inject_custom_styles(page.body);

        // Filters
        const filters = setup_filters();
        setup_filter_clear_buttons(filters);
        setup_filter_listeners(filters);

        // Pagination state
        let start = 0;
        let page_length = 50;
        let total_count = 0;
        let all_data = [];
        let datatable = null;

        // Initial Stats, Chart, and Table
        clear_stats();
        update_chart(null);
        load_report_table(true);

        // Setup table toggle functionality
        setup_table_toggle();

        /**
         * Render the main page layout.
         * @param {HTMLElement} body
         */
        function render_layout(body) {
            $(body).html(`
                <div class="container p-0">
                    <div class="row mb-3 align-items-center">
                        <div class="col">
                            <div class="section-title mb-2">🧾 Select Article</div>
                            <div class="row gx-2" id="filter-section-group-1"></div>
                        </div>
                        <div class="col-auto d-flex align-items-center" style="margin-top: 22px;">
                            <button class="btn btn-primary btn-xs clear-selections text-nowrap filter-clear-btn" id="clear-group-1">Clear All</button>
                        </div>
                    </div>
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
        }

        /**
         * Inject custom styles for the page.
         * @param {HTMLElement} body
         */
        function inject_custom_styles(body) {
            $(body).append(`
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
                    .dt-cell__content--col-0 {
                        width: unset !important;
                    }
                    /* Checkbox column alignment fix */
                    .dt-cell--col-0, .dt-header__cell--col-0 {
                        min-width: 40px !important;
                        max-width: 40px !important;
                        width: 40px !important;
                        text-align: center;
                    }
                    /* Table toggle section styles */
                    #table-toggle-section {
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border: 1px solid #dee2e6;
                    }
                    /* Compact Toggle Switch Styles */
                    .switch-compact {
                        position: relative;
                        display: inline-block;
                        width: 40px;
                        height: 20px;
                    }
                    
                    .switch-compact input {
                        opacity: 0;
                        width: 0;
                        height: 0;
                    }
                    
                    .slider-compact {
                        position: absolute;
                        cursor: pointer;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background-color: #ccc;
                        -webkit-transition: .3s;
                        transition: .3s;
                    }
                    
                    .slider-compact:before {
                        position: absolute;
                        content: "";
                        height: 14px;
                        width: 14px;
                        left: 3px;
                        bottom: 3px;
                        background-color: white;
                        -webkit-transition: .3s;
                        transition: .3s;
                    }
                    
                    input:checked + .slider-compact {
                        background-color: #2196F3;
                    }
                    
                    input:focus + .slider-compact {
                        box-shadow: 0 0 1px #2196F3;
                    }
                    
                    input:checked + .slider-compact:before {
                        -webkit-transform: translateX(20px);
                        -ms-transform: translateX(20px);
                        transform: translateX(20px);
                    }
                    
                    .slider-compact.round {
                        border-radius: 20px;
                    }
                    
                    .slider-compact.round:before {
                        border-radius: 50%;
                    }
                    
                    #table-toggle-section {
                        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                        border: 1px solid #dee2e6;
                    }
                </style>
            `);
        }

        /**
         * Setup all filters and return the filter controls object.
         * @returns {Object}
         */
        function setup_filters() {
            const currentYear = frappe.datetime.get_today().split('-')[0];
            return {
                cn_code: create_filter('CN Code', 'MultiSelectList', 'cn_code', '#filter-section-group-1'),
                supplier: create_filter('Supplier', 'MultiSelectList', 'supplier', '#filter-section-group-1'),
                article_number: create_filter('Article Number', 'MultiSelectList', 'article_number', '#filter-section-group-1'),
                reporting_period: create_filter('Reporting Period', 'MultiSelectList', 'reporting_period', '#filter-section-group-1'),
                year: create_filter('Year', 'Link', 'year', '#filter-section-group-2', null, 'Year', currentYear),
                ets_price_type: create_filter('ETS Price Type', 'Select', 'ets_price_type', '#filter-section-group-2', ['', 'Actual', 'Prediction'], null, 'Actual'),
                ets_price: create_filter('ETS Price', 'Select', 'ets_price', '#filter-section-group-2'),
            };
        }

        /**
         * Setup clear buttons for filter groups.
         * @param {Object} filters
         */
        function setup_filter_clear_buttons(filters) {
            $('#clear-group-1').on('click', () => {
                ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
                    filters[key]?.set_value([]);
                });
                load_report_table(true);
            });
            $('#clear-group-2').on('click', () => {
                ['ets_price_type', 'year', 'month', 'ets_price'].forEach(key => {
                    if (filters[key]) {
                        if (filters[key].df.fieldtype === 'MultiSelectList') {
                            filters[key].set_value([]);
                        } else {
                            filters[key].set_value(null);
                        }
                    }
                });
                load_report_table(true);
            });
        }

        /**
         * Setup listeners for filter changes.
         * @param {Object} filters
         */
        function setup_filter_listeners(filters) {
            ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
                const ctrl = filters[key];
                if (ctrl) {
                    ctrl.df.onchange = () => {
                        load_report_table(true);
                    };
                }
            });
            ['ets_price_type', 'year', 'month', 'ets_price'].forEach(key => {
                const ctrl = filters[key];
                if (ctrl) {
                    ctrl.df.onchange = () => {
                        const selected_filters = {
                            ets_price_type: filters.ets_price_type.get_value(),
                            year: filters.year.get_value(),
                            ets_price: filters.ets_price.get_value(),
                        };
                        update_stat_card_values(key, selected_filters);
                        if (key === 'ets_price_type' || key === 'year') {
                            refresh_ets_price_options(
                                filters.ets_price_type.get_value(),
                                filters.year.get_value()
                            );
                        }
                        load_report_table(true);
                    };
                }
            });
        }

        /**
         * Collect all selected filters and stat values from the DOM.
         * @returns {Object}
         */
        function get_all_selected_filters() {
            const selected_filters = {};
            ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
                selected_filters[key] = filters[key]?.get_value?.() || [];
            });
            ['ets_price_type', 'year', 'ets_price'].forEach(key => {
                selected_filters[key] = filters[key]?.get_value?.() || '';
            });
            selected_filters.cbam_factor = parseFloat($('[data-stat="cbam-factor"]').text()) || 0;
            selected_filters.bench_mark = parseFloat($('[data-stat="bench-mark-emission-value"]').text()) || 0;
            selected_filters.emission_value = parseFloat($('[data-stat="standard-emission-value"]').text()) || 0;
            selected_filters.ets_price_value = parseFloat($('[data-stat="ets-price"]').text()) || 0;
            return selected_filters;
        }

        /**
         * Refresh ETS Price options based on type and year.
         * @param {string} ets_price_type
         * @param {string|number} year
         */
        function refresh_ets_price_options(ets_price_type, year) {
            if (!ets_price_type || !year) return;
            frappe.db.get_list('ETS Carbon Price', {
                fields: ['name', 'price', 'price_date'],
                filters: { ets_price_type },
                order_by: 'price_date desc',
                limit: 100,
            }).then(res => {
                const prices = res
                    .filter(row => {
                        const y = frappe.datetime.str_to_obj(row.price_date).getFullYear();
                        return y == year;
                    })
                    .map(row => {
                        let dateStr = '';
                        if (row.price_date) {
                            const d = frappe.datetime.str_to_obj(row.price_date);
                            dateStr = ` (${d.getDate().toString().padStart(2, '0')}-${(d.getMonth()+1).toString().padStart(2, '0')}-${d.getFullYear()})`;
                        }
                        return {
                            label: `${row.price}${dateStr}`,
                            value: String(row.price)
                        };
                    });
                filters.ets_price.df.options = prices;
                filters.ets_price.refresh();
                if (prices.length) {
                    filters.ets_price.set_value(prices[0].value);
                }
            }).catch(() => {
                filters.ets_price.df.options = [];
                filters.ets_price.refresh();
            });
        }

        /**
         * Update stat card values based on filter changes.
         * @param {string} key
         * @param {Object} filters
         */
        function update_stat_card_values(key, filters) {
            if (key === 'ets_price') {
                $('.stat-value[data-stat="ets-price"]').text(filters.ets_price || 0.0);
                return;
            }
            clear_stats();
            frappe.call({
                method: 'cbam.cbam.page.financial_evaluation_report.financial_evaluation_report.get_cards_value',
                args: { filters },
                callback: function (r) {
                    if (!r.message) return;
                    const updated_values = {
                        'standard-emission-value': r.message.emission_value || 0.0,
                        'bench-mark-emission-value': r.message.bench_mark || 0.0,
                        'cbam-factor': r.message.cbam_factor || 0.0,
                        'ets-price': r.message.ets_price || 0.0,
                        'year': filters.year || frappe.datetime.get_today().split('-')[0],
                    };
                    Object.entries(updated_values).forEach(([key, val]) => {
                        $('.stat-value[data-stat="' + key + '"]').text(val);
                    });
                },
                error: function () {
                    clear_stats();
                }
            });
        }

        /**
         * Create a filter control and append to the parent selector.
         * @param {string} label
         * @param {string} fieldtype
         * @param {string} fieldname
         * @param {string} parentSelector
         * @param {Array|null} options
         * @param {string|null} link_to
         * @param {string|null} default_val
         * @returns {Object}
         */
        function create_filter(label, fieldtype, fieldname, parentSelector, options = null, link_to = null, default_val = null) {
            const df = { label, fieldname, fieldtype, options, default: default_val };
            if (link_to) df.options = link_to;
            if (fieldtype === 'MultiSelectList') {
                df.get_data = function (txt) {
                    const supplier_vals = filters.supplier?.get_value?.() || [];
                    const cn_code_vals = filters.cn_code?.get_value?.() || [];
                    if (fieldname === 'article_number') {
                        return frappe.db.get_list('External Good', {
                            fields: ['article_no as value', 'article_no as description'],
                            filters: [
                                ['article_no', 'like', `%${txt}%`],
                                supplier_vals.length ? ['supplier', 'in', supplier_vals] : null,
                                cn_code_vals.length ? ['cn_code', 'in', cn_code_vals] : null,
                            ].filter(Boolean),
                            distinct: true,
                            limit: 20,
                        });
                    }
                    if (fieldname === 'reporting_period') {
                        return frappe.db.get_list('External Good', {
                            fields: ['reporting_period as value', 'reporting_period as description'],
                            filters: [
                                ['name', 'like', `%${txt}%`],
                                supplier_vals.length ? ['supplier', 'in', supplier_vals] : null,
                                cn_code_vals.length ? ['cn_code', 'in', cn_code_vals] : null,
                            ].filter(Boolean),
                            distinct: true,
                            limit: 20,
                        });
                    }
                    if (fieldname === 'cn_code') {
                        return frappe.db.get_list('CN Code', {
                            fields: ['cn_code as value', 'cn_code as description'],
                            filters: [['cn_code', 'like', `%${txt}%`]],
                            limit: 20,
                        });
                    }
                    if (fieldname === 'supplier') {
                        return frappe.db.get_list('External Good', {
                            fields: ['supplier as value', 'supplier as description'],
                            filters: [['supplier', 'like', `%${txt}%`]],
                            distinct: true,
                            limit: 20,
                        });
                    }
                };
            }
            const $col = $('<div class="col mb-2"></div>').appendTo(parentSelector);
            const control = frappe.ui.form.make_control({ parent: $col, df });
            control.refresh();
            // Set default value in UI if provided
            if (default_val !== undefined && default_val !== null && default_val !== "") {
                control.set_value(default_val);
            }
            return control;
        }

        /**
         * Clear and render stat cards with default values.
         */
        function clear_stats() {
            const compact_stats = [
                { label: 'Standard Emission Value', value: '--' },
                { label: 'Bench Mark Emission Value', value: '--' },
                { label: 'CBAM Factor', value: '--' },
                { label: 'ETS Price', value: '--' },
                { label: 'Year', value: 2025 },
            ];
            $('#compact-stat-row').empty();
            compact_stats.forEach(stat => {
                $('#compact-stat-row').append(`<div class='col mb-2'>${render_compact_card(stat.label, stat.value)}</div>`);
            });
        }

        /**
         * Render or update the chart section.
         * @param {Object|null} chart_data
         */
        function update_chart(chart_data) {
            $('#chart-section').empty();

            if (!chart_data || !chart_data.labels || chart_data.labels.length === 0) {
                $('#chart-section').html('<div class="text-center text-muted p-4">No data available for chart</div>');
                return;
            }

            // Custom: Concatenate article and supplier for x-axis labels if available
            let labels = chart_data.labels;
            let label_map = {};
            if (chart_data.articles && chart_data.suppliers && Array.isArray(chart_data.articles) && Array.isArray(chart_data.suppliers)) {
                labels = chart_data.articles.map((article, idx) => {
                    const supplier = chart_data.suppliers[idx] || '';
                    const label = `${article} (${supplier})`;
                    label_map[idx] = label;
                    return label;
                });
            } else {
                labels = chart_data.labels;
                labels.forEach((l, idx) => { label_map[idx] = l; });
            }

            // Highcharts integration: create a scrollable container and chart div
            const minWidth = Math.max(600, labels.length * 80); // 80px per label as a heuristic
            $('#chart-section').append('<div id="highchart-scroll-inner" style="overflow-x: auto; width: 100%;"><div id="highchart-bar" style="min-width: ' + minWidth + 'px; max-height: 350px;"></div></div>');

            function renderHighChart() {
                Highcharts.chart('highchart-bar', {
                    chart: {
                        type: 'column',
                        height: 350
                    },
                    credits: {
                        enabled: false
                    },
                    title: { text: __('Standard vs Actual Cost') },
                    xAxis: {
                        categories: labels,
                        labels: {
                            rotation: 45,
                            style: { fontSize: '12px' }
                        }
                    },
                    yAxis: {
                        min: 0,
                        title: { text: __('Cost') }
                    },
                    legend: { align: 'center', verticalAlign: 'bottom', layout: 'horizontal' },
                    series: [
                        {
                            name: __('Actual Cost'),
                            data: chart_data.actual_costs,
                            color: '#3b5bdb'
                        },
                        {
                            name: __('Standard Cost'),
                            data: chart_data.standard_costs,
                            color: '#fa5252'
                        }
                    ]
                });
            }

            if (typeof window.Highcharts === 'undefined') {
                // Dynamically load Highcharts from CDN if not already loaded
                const script = document.createElement('script');
                script.src = 'https://code.highcharts.com/highcharts.js';
                script.onload = () => renderHighChart();
                document.head.appendChild(script);
            } else {
                renderHighChart();
            }
        }

        /**
         * Load and render the report table and update chart.
         * @param {boolean} reset If true, reset table and start from first page.
         * @param {Object} [filters={}]
         */
        function load_report_table(reset = false, filters = {}) {
            if (reset) {
                start = 0;
                all_data = [];
                if (datatable) {
                    datatable.destroy();
                    datatable = null;
                }
            }
            const selected_filters = get_all_selected_filters();
            frappe.call({
                method: 'cbam.cbam.page.financial_evaluation_report.financial_evaluation_report.get_report_data',
                args: { filters, selected_filters, start, page_length },
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
                        if (!datatable) {
                            $('#table-section').empty();
                            datatable = new DataTable('#table-section', {
                                columns: formattedColumns,
                                data: all_data,
                                layout: 'fixed',
                                stickyHeader: true,
                                inlineFilters: true,
                                scrollY: '500px',
                                scrollX: true,
                                className: 'frappe-datatable',
                                checkboxColumn: true, 
                            });
                        } else {
                            datatable.refresh(all_data);
                        }
                        update_chart(chart_data);
                        render_pagination_controls();
                    }
                },
                error: function () {
                    $('#table-section').empty().html('<div class="text-center text-muted p-4">Failed to load data</div>');
                    update_chart(null);
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

        /**
         * Render a compact stat card.
         * @param {string} label
         * @param {string|number} value
         * @returns {string}
         */
        function render_compact_card(label, value) {
            return `
                <div class="frappe-card d-flex flex-column justify-content-center align-items-center border rounded shadow-sm p-3 text-center stat-card h-100">
                    <div class="text-muted small">${label}</div>
                    <div class="fw-bold fs-5 mt-1 stat-value" data-stat="${label.toLowerCase().replace(/ /g, '-')}">${value}</div>
                </div>
            `;
        }

        /**
         * Setup table toggle functionality.
         */
        function setup_table_toggle() {
            // Table toggle functionality
            $('#table-toggle').on('change', function() {
                const isVisible = $(this).is(':checked');
                
                // You can add your custom actions here based on the toggle state
                console.log('Table toggle changed:', isVisible);
                
                // Example: Show/hide table
                if (isVisible) {
                    $('#table-scroll-container').show();
                    $('#pagination-controls').show();
                } else {
                    $('#table-scroll-container').hide();
                    $('#pagination-controls').hide();
                }
                
                // Add your custom logic here
                // For example:
                // - Trigger different data loading
                // - Change chart display
                // - Update filters
                // - Show/hide other sections
                // - etc.
            });
        }
    })();
};
