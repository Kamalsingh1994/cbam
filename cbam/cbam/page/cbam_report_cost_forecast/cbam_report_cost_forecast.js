// Copyright (c) 2024, CBAM Team. All rights reserved.
// MIT License. See license.txt

frappe.provide('cbam.pages');

frappe.pages['cbam-report-cost-forecast'].on_page_load = function(wrapper) {

    if (!sessionStorage.getItem('cbam_report_cost_forecast_reloaded')) {
        sessionStorage.setItem('cbam_report_cost_forecast_reloaded', '1');
        location.reload();
        return;
    } else {
        sessionStorage.removeItem('cbam_report_cost_forecast_reloaded');
    }
    $(wrapper).empty();
    
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('CBAM Report Cost Forecast'),
        single_column: true,
    });

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
        #dashboard-tabs {
          margin-left: 0 !important;
          margin-right: 0 !important;
          margin-bottom: 25px !important;
        }
      </style>`).appendTo('head');
  
    // Insert tab navigation at the top of .page-content for perfect alignment
    $('.page-content').prepend(`
        <ul class="nav nav-tabs mb-0" id="dashboard-tabs">
            <li class="nav-item">
                <a class="nav-link" href="/app/ets-price-dashboard">ETS Price Dashboard</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="/app/financial-evaluation-report">Financial Evaluation Report</a>
            </li>
            <li class="nav-item">
                <a class="nav-link active" href="/app/cbam-report-cost-forecast">CBAM Report Cost Forecast</a>
            </li>
        </ul>
    `);


    // State
    let start = 0;
    let page_length = 50;
    let total_count = 0;
    let all_data = [];
    let datatable = null;
    let filters = {};

    // Render layout and setup filters
    render_layout(page.body);
    filters = setup_filters();

    // Set default CBAM Report after filters are set up
    frappe.call({
        method: 'cbam.cbam.page.cbam_report_cost_forecast.cbam_report_cost_forecast.get_default_cbam_report',
        callback: function(r) {
            if (r.message && filters.cbam_report) {
                filters.cbam_report.set_value([r.message]);
                start = 0;
                all_data = [];
                load_report_table(true);
            }
        }
    });

    // Initial Table and Chart
    load_report_table(true);

    // --- Layout ---
    function render_layout(body) {
        $(body).html(`
            <div class="container p-0">
                <div class="frappe-card mb-3" id="filter-card-section">
                    <div class="row align-items-center">
                        <div class="col-md-3">
                            <div class="row gx-2" id="filter-section-group-1"></div>
                        </div>
                        <div class="col-md-2" id="from-year-link"></div>
                        <div class="col-md-2" id="to-year-link"></div>
                    </div>
                </div>

                <div id="chart-section-container" class="frappe-card mb-4 p-3">
                    <div id="chart-section"></div>
                </div>
                <div class="frappe-card mb-4" id="table-scroll-container" style="overflow-x: auto;">
                    <div id="table-section"></div>
                </div>
            </div>
        `);
    }

    // --- Filter Setup ---
    function setup_filters() {
        const filters = {
            cbam_report: cbam.create_filter('CBAM Report', 'MultiSelectList', 'cbam_report', '#filter-section-group-1', []),
            from_year: cbam.create_filter('From Year', 'Link', 'from_year', '#from-year-link', 'Year'),
            to_year: cbam.create_filter('To Year', 'Link', 'to_year', '#to-year-link', 'Year'),
        };
        // From Year Link: auto fetch from Year DocType
        filters.from_year.df.get_data = function(txt) {
            return frappe.db.get_list('Year', {
                fields: ['year as value', 'year as description'],
                filters: txt ? [['year', 'like', `%${txt}%`]] : [],
                limit: 20,
            });
        };

        // To Year Link: auto fetch from Year DocType
        filters.to_year.df.get_data = function(txt) {
            return frappe.db.get_list('Year', {
                fields: ['name as value', 'name as description'],
                filters: txt ? [['name', 'like', `%${txt}%`]] : [],
                limit: 20,
            });
        };
        // Fetch CBAM Report options
        filters.cbam_report.df.get_data = function(txt) {
            return frappe.db.get_list('CBAM Report', {
                fields: ['name as value', 'report_id as description'],
                filters: txt ? [['report_id', 'like', `%${txt}%`]] : [],
                limit: 20,
            });
        };

        // Dynamic event: reload table/chart on change
        filters.cbam_report.df.onchange = function() {
            start = 0;
            all_data = [];
            page_length = 50;
            load_report_table(true);
        };

        filters.from_year.df.onchange = function() {
            start = 0;
            all_data = [];
            page_length = 50;
            load_report_table(true);
        };

        filters.to_year.df.onchange = function() {
            start = 0;
            all_data = [];
            page_length = 50;
            load_report_table(true);
        };


        return filters;
    }

    // --- Data Table and Chart ---
    function load_report_table(reset = false) {
        const selected_reports = filters.cbam_report.get_value();
        const from_year = filters.from_year ? filters.from_year.get_value() : null;
        const to_year = filters.to_year ? filters.to_year.get_value() : null;
        if (reset) {
            start = 0;
            all_data = [];
            total_count = 0;
            if (datatable) {
                datatable.destroy();
                datatable = null;
            }
        }
        if (!selected_reports || !selected_reports.length) {
            $('#table-section').html('<div class="text-center text-muted p-4">Please select at least one CBAM Report to view data.</div>');
            $('#chart-section').html('<div class="text-center text-muted p-4">No chart data available. Please select at least one CBAM Report.</div>');
            $('#pagination-controls').remove();
            return;
        }
        frappe.call({
            method: 'cbam.cbam.page.cbam_report_cost_forecast.cbam_report_cost_forecast.get_cbam_report_data',
            args: {
                cbam_reports: selected_reports,
                start,
                page_length,
                from_year,
                to_year
            },
            freeze: true,
            callback: function(r) {
                if (r.message) {
                    const { columns, data, chart_data, total_count: count } = r.message;
                    total_count = count || total_count;
                    if (reset) {
                        all_data = data || [];
                    } else {
                        all_data = all_data.concat(data || []);
                    }
                    render_table(columns, all_data);
                    render_chart(chart_data);
                    render_pagination_controls();
                } else {
                    $('#table-section').html('<div class="text-center text-muted p-4">No data found for selected CBAM Report(s).</div>');
                    $('#chart-section').html('<div class="text-center text-muted p-4">No chart data available for the selected filters.</div>');
                    $('#pagination-controls').remove();
                }
            },
            error: function() {
                $('#table-section').html('<div class="text-center text-muted p-4">Failed to load data</div>');
                $('#chart-section').html('<div class="text-center text-muted p-4">No chart data available for the selected filters.</div>');
                $('#pagination-controls').remove();
            }
        });
    }

    function render_table(columns, data) {
        if (!data.length) {
            $('#table-section').html('<div class="text-center text-muted p-4">No data found for selected CBAM Report(s).</div>');
            return;
        }
        if (!datatable) {
            $('#table-section').empty();
            datatable = new DataTable('#table-section', {
                columns: columns,
                data: data,
                layout: 'fixed',
                stickyHeader: true,
                scrollY: '500px',
                scrollX: true,
                className: 'frappe-datatable',
            });
        } else {
            datatable.refresh(data);
        }
    }

    function render_chart(chart_data) {
        $('#chart-section').empty();

        if (!chart_data || !chart_data.categories || !chart_data.series || chart_data.categories.length === 0) {
            $('#chart-section').html('<div class="text-center text-muted p-4">No chart data available for the selected filters.</div>');
            return;
        }
        if (typeof Highcharts === 'undefined') {
            load_highcharts(() => render_chart(chart_data));
            return;
        }

        // Do NOT set min-width or use a scrollable wrapper. Let Highcharts fit the chart to the container.
        Highcharts.chart('chart-section', {
            chart: {
                type: 'column',
                height: 400,
                zoomType: 'x' // Enable default Highcharts zoom and reset zoom button
            },
            credits: { enabled: false },
            title: { text: 'Total Actual vs Standard Cost by Year' },
            xAxis: {
                categories: chart_data.categories,
                labels: { rotation: 45, style: { fontSize: '12px' } },
                title: { text: 'Year' }
            },
            yAxis: { min: 0, title: { text: 'Cost' } },
            series: [
                { ...chart_data.series[0], color: '#003366' },
                chart_data.series[1]
            ],
            plotOptions: {
                column: {
                    grouping: true,
                    shadow: false,
                    borderWidth: 0,
                    pointPadding: 0, // No gap between bars in a group
                    groupPadding: 0.1, // No gap between groups
                    maxPointWidth: 40 // Limit bar width for small datasets
                }
            }
        });
    }

    function load_highcharts(callback) {
        const script = document.createElement('script');
        script.src = 'https://code.highcharts.com/highcharts.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    function render_pagination_controls() {
        $('#pagination-controls').remove();
        if (!all_data.length) return;
        const showing_from = total_count === 0 ? 0 : 1;
        const showing_to = all_data.length;
        const html = `
            <div id="pagination-controls" class="cbam-pagination-footer d-flex flex-wrap align-items-center justify-content-between mt-2">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="mx-2">Showing <b>${showing_from}&ndash;${showing_to}</b> of <b>${total_count}</b></span>
                    <span class="mx-2">| Rows per load: </span>
                    <select id="page-length-select" class="form-select form-select-sm d-inline-block w-auto">
                        <option value="20">20</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="500">500</option>
                    </select>
                </div>
                <div class="ms-auto">
                    <button id="load-more" class="btn btn-primary btn-sm px-2" ${(all_data.length >= total_count) ? 'disabled' : ''}>Load More</button>
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
        $('#table-scroll-container').after(html);
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
};
