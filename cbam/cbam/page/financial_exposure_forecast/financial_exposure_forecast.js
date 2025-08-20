// Copyright (c) 2024, CBAM Team. All rights reserved.
// MIT License. See license.txt

frappe.provide('cbam.pages');

frappe.pages['financial-exposure-forecast'].on_page_load = function(wrapper) {

    if (!sessionStorage.getItem('financial_exposure_forecast_reloaded')) {
        sessionStorage.setItem('financial_exposure_forecast_reloaded', '1');
        location.reload();
        return;
    } else {
        sessionStorage.removeItem('financial_exposure_forecast_reloaded');
    }
    $(wrapper).empty();
    
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Financial Dashboard'),
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
            <!-- <li class="nav-item">
                <a class="nav-link" href="/app/ets-price-dashboard">ETS Price Dashboard</a>
            </li> -->
			<li class="nav-item">
                <a class="nav-link active" href="/app/financial-exposure-forecast">Financial Exposure Forecast</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="/app/various-cost-comparisons">Various Cost Comparisons</a>
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

    // Set all CBAM Reports by default after filters are set up
    frappe.call({
        method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_all_cbam_reports',
        callback: function(r) {
            if (r.message && r.message.length > 0 && filters.cbam_report) {
                filters.cbam_report.set_value(r.message);
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

        // Custom width for CBAM Report filter - make it wider since it's the only filter in this group
            const cbamReportContainer = $('#filter-section-group-1 .frappe-control');
            if (cbamReportContainer.length > 0) {
                cbamReportContainer.closest('.col-3').removeClass('col-3').addClass('col-8');
            }

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
            method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_cbam_report_data',
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
                    load_highcharts(() => render_chart(chart_data));
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
                checkboxColumn: true,
                events: {
                    onCheckRow: update_export_button_state,
                    onUncheckRow: update_export_button_state,
                }
            });
        } else {
            datatable.refresh(data);
            update_export_button_state();
        }
    }


    // Helper: Map data to month categories, only at quarter-end months
    function mapDataToMonths(data, categories, originalCategories) {
        const arr = Array(categories.length).fill(null);
        originalCategories.forEach((cat, i) => {
            const [mon, yr] = cat.split(' ');
            const monthIdx = new Date(Date.parse(mon + ' 1, 2000')).getMonth();
            const shortLabel = new Date(yr, monthIdx, 1).toLocaleString('default', { month: 'short' }) + ' ' + yr;
            const longLabel = new Date(yr, monthIdx, 1).toLocaleString('default', { month: 'long' }) + ' ' + yr;
            const idx = categories.findIndex(c =>
                c.trim().toLowerCase() === shortLabel.toLowerCase() ||
                c.trim().toLowerCase() === longLabel.toLowerCase()
            );
            if (idx !== -1) arr[idx] = data[i];
        });
        return arr;
    }

    // Helper: Build month categories for the full range
    function getMonthCategories(startYear, endYear) {
        const months = [];
        for (let year = startYear; year <= endYear; year++) {
            for (let m = 0; m < 12; m++) {
                const date = new Date(year, m, 1);
                const label = date.toLocaleString('default', { month: 'short' }) + ' ' + year;
                months.push(label);
            }
        }
        return months;
    }

    // Helper: Format due date as '31 Dec 2025'
    function formatDueDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        if (isNaN(d)) return dateStr;
        const day = d.getDate().toString().padStart(2, '0');
        const month = d.toLocaleString('default', { month: 'short' });
        const year = d.getFullYear();
        return `${day} ${month} ${year}`;
    }

    function ensureObjectPoints(arr) {
        return arr.map(pt => {
            if (pt && typeof pt === 'object' && 'y' in pt) return pt;
            return {y: pt === null || pt === undefined ? null : pt, required_certificates: null};
        });
    }

    function render_chart(chart_data) {
        // Remove any existing toggle switch to prevent duplicates
        $('.tooltip-toggle-container').remove();
        
        // Add toggle switch above the chart
        const toggleHtml = `
            <div class="tooltip-toggle-container mb-3" style="text-align: center;">
                <div class="btn-group" role="group" aria-label="Tooltip Display Toggle">
                    <input type="radio" class="btn-check" name="tooltip-view" id="view-cost" checked>
                    <label class="btn btn-outline-primary" for="view-cost">
                        <i class="fas fa-euro-sign"></i> Amount Due in €
                    </label>
                    
                    <input type="radio" class="btn-check" name="tooltip-view" id="view-certificates">
                    <label class="btn btn-outline-primary" for="view-certificates">
                        Required Certificates
                    </label>
                    
                    <input type="radio" class="btn-check" name="tooltip-view" id="view-both">
                    <label class="btn btn-outline-primary" for="view-both">
                        Both Views
                    </label>
                </div>
            </div>
            <style>
                .tooltip-toggle-container {
                    background: #f8f9fa;
                    border: 1px solid #e3e6eb;
                    border-radius: 0.5rem;
                    padding: 1rem;
                    margin-bottom: 1rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .tooltip-toggle-container .btn-group {
                    display: inline-flex;
                    flex-wrap: wrap;
                    gap: 0.25rem;
                }
                .tooltip-toggle-container .btn {
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    padding: 0.5rem 1rem;
                    transition: all 0.2s ease;
                    background-color: #ffffff;
                    border-color: #000000;
                    color: #000000;
                }
                .tooltip-toggle-container .btn-check {
                    display: none;
                }
                .tooltip-toggle-container .btn-check:checked + .btn {
                    background-color: #000000 !important;
                    border-color: #000000 !important;
                    color: white !important;
                    box-shadow: 0 0 0 0.2rem rgba(0, 0, 0, 0.25);
                }
                .tooltip-toggle-container .btn:hover:not(.btn-check:checked + .btn) {
                    background-color: #e9ecef;
                    border-color: #adb5bd;
                    color: #495057;
                }
                .tooltip-toggle-container .btn-check:checked + .btn:hover {
                    background-color: #333333 !important;
                    border-color: #000000 !important;
                }
                .tooltip-toggle-container .btn:focus {
                    box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
                    outline: none;
                }
                @media (max-width: 768px) {
                    .tooltip-toggle-container .btn-group {
                        flex-direction: column;
                        width: 100%;
                    }
                    .tooltip-toggle-container .btn {
                        width: 100%;
                        margin-bottom: 0.25rem;
                    }
                }
            </style>
        `;
        
        // Insert toggle above the chart
        $('#chart-section').before(toggleHtml);
        
        // Store the current view preference
        let currentTooltipView = 'cost'; // 'cost', 'certificates', or 'both'
        
        // Handle toggle changes
        $('input[name="tooltip-view"]').on('change', function() {
            currentTooltipView = this.id.replace('view-', '');
            console.log('Tooltip view changed to:', currentTooltipView);
            
            // Ensure only one option is selected
            $('input[name="tooltip-view"]').prop('checked', false);
            $(this).prop('checked', true);
            
            // Add visual feedback
            $('.tooltip-toggle-container .btn').removeClass('active');
            $(this).next('label').addClass('active');
        });
        
        // Initialize the first option as selected
        $('#view-cost').prop('checked', true);
        $('#view-cost').next('label').addClass('active');
        
        // Extract and prepare categories
        let categories = chart_data.categories || [];
        let yearDueDatesMap = chart_data.year_due_dates || {};
        const actualData = chart_data.series[0]?.data || [];
        const forecastData = chart_data.series[1]?.data || [];

        // Calculate accumulated exposure (cumulative sum)
        const accumulatedExposure = [];
        let cumulative = 0;
        for (let i = 0; i < categories.length; i++) {
            const value = actualData[i] ?? forecastData[i];
            if (value !== null && value !== undefined) {
                cumulative += value;
            }
            accumulatedExposure.push(cumulative);
        }

        // Calculate per-year accumulated exposure and diamond positions
        const minRequiredActual = [];
        const minRequiredForecast = [];
        let yearAccum = 0;
        let year = null;
        for (let i = 0; i < categories.length; i++) {
            // Extract year from category label (e.g., 'March 2025')
            const match = categories[i].match(/\b(\d{4})\b/);
            const thisYear = match ? match[1] : null;
            if (thisYear !== year) {
                year = thisYear;
                yearAccum = 0;
            }
            const value = actualData[i] ?? forecastData[i];
            if (value && value > 0) {
                yearAccum += value;
            }
            if (actualData[i] && actualData[i] > 0) {
                minRequiredActual.push(yearAccum * 0.5);
                minRequiredForecast.push(null);
            } else if (forecastData[i] && forecastData[i] > 0) {
                minRequiredActual.push(null);
                minRequiredForecast.push(yearAccum * 0.5);
            } else {
                minRequiredActual.push(null);
                minRequiredForecast.push(null);
            }
        }

        // Carefully extend categories to include all months from the earliest year in your data up to the latest due date
        const allYears = categories.map(cat => parseInt(cat.match(/\b(\d{4})\b/)[1])).filter(Boolean);
        const minYear = Math.min(...allYears);
        const allDueDates = Object.values(yearDueDatesMap).map(d => new Date(d));
        const latestDueDate = new Date(Math.max(...allDueDates.map(d => d.getTime())));
        const maxYear = latestDueDate.getFullYear();
        const maxMonth = latestDueDate.getMonth(); // 0-based
        const monthCategories = [];
        for (let year = minYear; year <= maxYear; year++) {
            for (let m = 0; m < 12; m++) {
                if (year === maxYear && m > maxMonth) break;
                const date = new Date(year, m, 1);
                const label = date.toLocaleString('default', { month: 'short' }) + ' ' + year;
                monthCategories.push(label);
            }
        }
        categories = monthCategories;

        // Remap all data series to only appear at quarter-ends
        const actualDataMonth = mapDataToMonths(actualData, categories, chart_data.categories || []);
        const forecastDataMonth = mapDataToMonths(forecastData, categories, chart_data.categories || []);
        const minRequiredActualMonth = mapDataToMonths(minRequiredActual, categories, chart_data.categories || []);
        const minRequiredForecastMonth = mapDataToMonths(minRequiredForecast, categories, chart_data.categories || []);
        const accumulatedExposureMonth = mapDataToMonths(accumulatedExposure, categories, chart_data.categories || []);

        // Build yearDueDates array for plotLines
        let yearDueDates = [];
        let lastYear = null;
        categories.forEach((cat, idx) => {
            const match = cat.match(/\b(\d{4})\b/);
            const thisYear = match ? match[1] : null;
            if (thisYear !== lastYear && lastYear !== null) {
                yearDueDates.push({ idx: idx - 1, year: lastYear });
            }
            lastYear = thisYear;
        });
        if (categories.length > 0 && lastYear) {
            yearDueDates.push({ idx: categories.length - 1, year: lastYear });
        }
        
        // Debug: log due date, label, index, and categories for each plotLine
        Object.entries(yearDueDatesMap).forEach(([reportingYear, dueDateRaw]) => {
            const d = new Date(dueDateRaw);
            const monthShort = d.toLocaleString('default', { month: 'short' });
            const monthLong = d.toLocaleString('default', { month: 'long' });
            const yearStr = d.getFullYear().toString();
            const idx = categories.findIndex(cat => {
                const c = cat.trim().toLowerCase();
                return (
                    c === `${monthShort} ${yearStr}`.toLowerCase() ||
                    c === `${monthLong} ${yearStr}`.toLowerCase()
                );
            });
        });
        
        // Plot a vertical line for every reporting year at its due date (even if due date is in the following year)
        const plotLines = Object.entries(yearDueDatesMap).map(([reportingYear, dueDateRaw]) => {
            const d = new Date(dueDateRaw);
            const monthShort = d.toLocaleString('default', { month: 'short' });
            const monthLong = d.toLocaleString('default', { month: 'long' });
            const yearStr = d.getFullYear().toString();
            // Robustly find the index in categories for the due date month and year
            const idx = categories.findIndex(c => {
                const cstr = c.trim().toLowerCase();
                return (
                    cstr === `${monthShort} ${yearStr}`.toLowerCase() ||
                    cstr === `${monthLong} ${yearStr}`.toLowerCase()
                );
            });
            // Subtract one from the reporting year for the label
            const labelYear = (parseInt(reportingYear, 10) - 1).toString();
            const labelText = `${labelYear} Due: ${formatDueDate(dueDateRaw)}`;
            return {
                value: idx,
                color: '#ff0000',
                width: 2,
                dashStyle: 'Dash',
                label: {
                    text: labelText,
                    rotation: 270, // vertical label
                    x: 20,         // horizontal gap from the line
                    y: 120,        // negative value to center vertically on the line
                    style: { color: '#ff0000', fontWeight: 'bold' },
                    align: 'center'
                },
                zIndex: 5
            };
        });

        // Add a line from December of the previous year to the due date, and a diamond at the due date
        const extraLineSeries = [];
        const extraDiamondSeries = [];
        Object.entries(yearDueDatesMap).forEach(([reportingYear, dueDateRaw]) => {
            // Use previous year for December
            const prevYear = (parseInt(reportingYear, 10) - 1).toString();
            const decLabelShort = 'Dec ' + prevYear;
            const decLabelLong = 'December ' + prevYear;
            const decIdx = categories.findIndex(cat =>
                cat.trim().toLowerCase() === decLabelShort.toLowerCase() ||
                cat.trim().toLowerCase() === decLabelLong.toLowerCase()
            );

            // Find the last non-null value in accumulatedExposureMonth for the previous year
            const yearIndices = categories
                .map((cat, idx) => ({ cat, idx }))
                .filter(({ cat }) => cat.endsWith(prevYear))
                .map(({ idx }) => idx);

            let value = null;
            for (let i = yearIndices.length - 1; i >= 0; i--) {
                const idx = yearIndices[i];
                if (accumulatedExposureMonth[idx] !== null) {
                    value = accumulatedExposureMonth[idx];
                    break;
                }
            }

            // Find due date index
            const d = new Date(dueDateRaw);
            const dueMonthShort = d.toLocaleString('default', { month: 'short' });
            const dueMonthLong = d.toLocaleString('default', { month: 'long' });
            const dueYearStr = d.getFullYear().toString();
            const dueIdx = categories.findIndex(cat => {
                const c = cat.trim().toLowerCase();
                return (
                    c === `${dueMonthShort} ${dueYearStr}`.toLowerCase() ||
                    c === `${dueMonthLong} ${dueYearStr}`.toLowerCase()
                );
            });

            if (decIdx !== -1 && dueIdx !== -1 && value !== null) {
                // Add the connecting line
                extraLineSeries.push({
                    name: `Accumulated Exposure to Due (${reportingYear})`,
                    type: 'line',
                    color: 'rgb(135, 206, 235)', // changed to blue
                    lineWidth: 2,
                    dashStyle: 'Dash', // make the line dashed
                    marker: { enabled: false },
                    data: [
                        [decIdx, value],
                        [dueIdx, value]
                    ],
                    enableMouseTracking: false,
                    showInLegend: false,
                    zIndex: 2
                });
                // Add the diamond at the due date
                extraDiamondSeries.push({
                    name: `Due Diamond (${reportingYear})`,
                    type: 'scatter',
                    color: 'rgb(135, 206, 235)', // changed to blue
                    marker: {
                        symbol: 'diamond',
                        fillColor: '#fff',
                        lineColor: 'rgb(135, 206, 235)', // changed to blue
                        lineWidth: 2,
                        radius: 8
                    },
                    data: [[dueIdx, value]],
                    enableMouseTracking: false,
                    showInLegend: false,
                    zIndex: 3
                });
            }
        });

        // Only sanitize main cost/forecast series before rendering chart
        if (Array.isArray(chart_data.series)) {
            chart_data.series.forEach(s => { s.data = ensureObjectPoints(s.data); });
        }
        // Do NOT touch overlays/diamonds logic at all
        Highcharts.chart('chart-section', {
            chart: {
                type: 'column',
                height: 600,
                zoomType: 'x',
                spacingBottom: 20 // reduced from 100
            },
            credits: { enabled: false },
            title: { text: 'Financial Exposure Forecast' },
            xAxis: {
                categories: categories,
                labels: { rotation: 45, style: { fontSize: '12px' } },
                title: { text: 'Month' },
                plotLines: plotLines
            },
            yAxis: {
                min: 0,
                title: { text: 'Financial Exposure over Time [€]' }
            },
            series: [
                {
                    name: 'Quarterly Financial Exposure Based on Real Data',
                    data: actualDataMonth,
                    color: '#003366',
                    type: 'column',
                    zIndex: 2
                },
                {
                    name: 'Quarterly Financial Exposure Based on Forecasts',
                    data: forecastDataMonth,
                    color: '#87ceeb',
                    type: 'column',
                    borderColor: '#5fa7c6',
                    borderWidth: 2,
                    zIndex: 2
                },
                {
                    name: 'Accumulated Financial Exposure Based on Forecasts',
                    data: accumulatedExposureMonth,
                    type: 'scatter',
                    color: '#87ceeb',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 6,
                        fillColor: '#87ceeb',
                        lineWidth: 2,
                        lineColor: '#87ceeb'
                    },
                    zIndex: 1
                },
                {
                    name: 'Minimum Required Account Balance',
                    data: minRequiredActualMonth,
                    type: 'scatter',
                    marker: {
                        symbol: 'diamond',
                        fillColor: '#fff',
                        lineColor: '#003366',
                        lineWidth: 2,
                        radius: 7
                    },
                    color: '#003366',
                    showInLegend: true,
                    zIndex: 3
                },
                {
                    name: 'Minimum Required Account Balance Based on Forecast',
                    data: minRequiredForecastMonth,
                    type: 'scatter',
                    marker: {
                        symbol: 'diamond',
                        fillColor: '#fff',
                        lineColor: '#87ceeb',
                        lineWidth: 2,
                        radius: 7
                    },
                    color: '#87ceeb',
                    showInLegend: true,
                    zIndex: 3
                },
                ...extraLineSeries,
                ...extraDiamondSeries
            ],
            plotOptions: {
                column: {
                    grouping: false,
                    shadow: false,
                    borderWidth: 0,
                    pointPadding: 0.1,
                    groupPadding: 0.1,
                    maxPointWidth: 40
                }
            },
            tooltip: {
                shared: false,
                useHTML: true,
                formatter: function() {
                    // Show content based on toggle selection
                    let cost = this.y;  // Use this.y directly
                    let certText = '';
                    let costDisplay = '';
                    
                    // Calculate certificates for ALL series if ETS price is available
                    if (cost !== null && !isNaN(cost) && typeof this.point.index === 'number' && Array.isArray(chart_data.ets_prices)) {
                        let ets_price = chart_data.ets_prices[this.point.index];
                        
                        // Frontend fallback: if index is beyond array length, use last available price
                        if (ets_price === undefined && chart_data.ets_prices.length > 0) {
                            ets_price = chart_data.ets_prices[chart_data.ets_prices.length - 1];
                        }
                        
                        // Validate ETS price before calculation
                        if (ets_price && !isNaN(ets_price) && isFinite(ets_price) && ets_price > 0) {
                            let certificates = cost / ets_price;
                            
                            // Validate certificate calculation result
                            if (!isNaN(certificates) && isFinite(certificates) && certificates >= 0) {
                                // Only show certificates for diamond/overlay series
                                if (this.series.name.includes('ETS Certificates') || this.series.name.includes('Minimum Required Account Balance')) {
                                    certText = `<br/><span style=\"color:#888\">Required Certificates:</span> <b>${certificates.toLocaleString(undefined, {maximumFractionDigits: 2})}</b>`;
                                }
                            }
                        }
                    }
                    
                    // Always prepare cost display
                    if (cost !== null && !isNaN(cost)) {
                        costDisplay = `€${cost.toLocaleString()}`;
                    } else {
                        costDisplay = '€0';  // Fallback if no cost
                    }
                    
                    // Show different labels based on series type
                    let seriesLabel = '';
                    if (this.series.name.includes('ETS Certificates') || this.series.name.includes('Minimum Required Account Balance')) {
                        // For diamond/overlay series, show "Amount Due"
                        seriesLabel = 'Amount Due';
                    } else {
                        // For main bars, show the original series name
                        seriesLabel = this.series.name;
                    }
                    
                    // Build tooltip content based on toggle selection
                    let tooltipContent = '';
                    
                    // Get current toggle selection
                    const selectedView = $('input[name="tooltip-view"]:checked').attr('id').replace('view-', '');
                    
                    switch(selectedView) {
                        case 'cost':
                            // Show only Amount Due
                            tooltipContent = `<b>${this.x}</b><br/>
                                <span style=\"color:${this.color}\">●</span> ${seriesLabel}: <b>${costDisplay}</b>`;
                            break;
                            
                        case 'certificates':
                            // Show only Required Certificates (if available)
                            if (certText) {
                                tooltipContent = `<b>${this.x}</b><br/>
                                    <span style=\"color:${this.color}\">●</span> Required Certificates: <b>${certText.replace('<br/><span style=\"color:#888\">Required Certificates:</span> ', '')}</b>`;
                            } else {
                                // Fallback to cost if no certificates available
                                tooltipContent = `<b>${this.x}</b><br/>
                                    <span style=\"color:${this.color}\">●</span> ${seriesLabel}: <b>${costDisplay}</b>`;
                            }
                            break;
                            
                        case 'both':
                        default:
                            // Show both Amount Due and Required Certificates
                            tooltipContent = `<b>${this.x}</b><br/>
                                <span style=\"color:${this.color}\">●</span> ${seriesLabel}: <b>${costDisplay}</b>${certText}`;
                            break;
                    }
                    
                    return tooltipContent;
                }
            },
            legend: {
                enabled: true,
                useHTML: true,
                labelFormatter: function() {
                    if (this.name === 'Quarterly Financial Exposure Based on Real Data') {
                        return '<span style="color:#003366">●</span> ' + this.name;
                    } else if (this.name === 'Quarterly Financial Exposure Based on Forecasts') {
                        return '<span style="color:#87ceeb">●</span> ' + this.name;
                    } else if (this.name === 'Accumulated Financial Exposure Based on Forecasts') {
                        return '<span style="color:#87ceeb">---○</span> ' + this.name;
                    } else if (this.name === 'Minimum Required Account Balance') {
                        return '<span style="color:#003366">◆</span> ' + this.name;
                    } else if (this.name === 'Minimum Required Account Balance Based on Forecast') {
                        return '<span style="color:#87ceeb">◆</span> ' + this.name;
                    }
                    return this.name;
                }
            }
        });
    }

    // Loader for Highcharts
    function load_highcharts(callback) {
        if (typeof Highcharts !== 'undefined') {
            callback();
            return;
        }
        const script = document.createElement('script');
        script.src = 'https://code.highcharts.com/highcharts.js';
        script.onload = callback;
        document.head.appendChild(script);
    }
    function update_export_button_state() {
            const selected = datatable?.rowmanager?.getCheckedRows?.() || [];
            $('#export').prop('disabled', selected.length === 0);
    }
    function get_selected_rows_data() {
        const selectedIndexes = datatable?.rowmanager?.getCheckedRows?.() || [];
        return selectedIndexes.map(i => datatable.datamanager.data[i]);
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
        link.setAttribute("download", "cbam-report-cost-forecast.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
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
