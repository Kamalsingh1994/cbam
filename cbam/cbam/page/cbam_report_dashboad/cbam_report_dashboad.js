// Copyright (c) 2024, CBAM Team. All rights reserved.
// MIT License. See license.txt

frappe.provide('cbam.pages');

frappe.pages['cbam-report-dashboad'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('CBAM Report Dashboard'),
        single_column: true,
    });

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
                    </div>
                </div>

				 <div id="chart-section-container" class="frappe-card mb-4 p-3">
					<div id="chart-scroll-wrapper" style="overflow-x: auto; width: 100%; margin-bottom:-12px">
						<div id="chart-section" style="min-width: 1800px;"></div>
					</div>
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
            cbam_report: cbam.create_filter('CBAM Report', 'MultiSelectList', 'cbam_report', '#filter-section-group-1', [])
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
        return filters;
    }

    // --- Data Table and Chart ---
    function load_report_table(reset = false) {
        const selected_reports = filters.cbam_report.get_value();
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
            method: 'cbam.cbam.page.cbam_report_dashboad.cbam_report_dashboad.get_cbam_report_data',
            args: { cbam_reports: selected_reports, start, page_length },
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

        // Set min-width dynamically for scroll (60px per category, min 1800px)
        const minWidth = Math.max(1800, chart_data.categories.length * 60);
        $('#chart-section').css('min-width', minWidth + 'px');

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
                    pointPadding: 0.1,
                    groupPadding: 0.05
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
