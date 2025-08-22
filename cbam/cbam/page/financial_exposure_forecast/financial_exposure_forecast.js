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
        .fs-cont{
            height: 60px;
        }
        #annual-exposure-cards{
            height: 60px;
        }
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
    let filters; // Declare filters globally

    // Render layout and setup filters
    render_layout(page.body);
    filters = setup_filters();

    // Initial data loading will happen after year filter is populated
    // This ensures we respect the year filter from the start

    // --- Layout ---
    function render_layout(body) {
        $(body).html(`
            <div class="container p-0">
                <div class="frappe-card mb-3" id="filter-card-section">
                    <div class="row align-items-center fs-cont">
                        <div class="col-md-3">
                            <div class="row gx-2" id="filter-section-group-1"></div>
                        </div>
                        <div class="col-md-2" id="from-year-link"></div>
                        <div class="col-md-2" id="to-year-link"></div>
                    </div>
                </div>

                <!-- Annual Exposure Stat Cards -->
                <div class="frappe-card mb-3 p-2">
                    <div class="d-flex flex-wrap" id="annual-exposure-cards" style="gap: 16px;">
                        <!-- Cards will be populated dynamically -->
                    </div>
                </div>
                
                <div id="chart-section-container" class="frappe-card mb-4 p-3">
                    <div id="chart-section"></div>
                </div>
                
                <!-- Disclaimer Box -->
                <div class="frappe-card mb-4 p-3" style="background-color: #f8f9fa; border-left: 4px solid #007bff;">
                    <div class="d-flex align-items-center">
                        <i class="fa fa-info-circle text-primary me-2" style="font-size: 1.2em;"></i>&nbsp;
                        <div>
                            <strong class="text-primary">Note: </strong> For the financial exposure calculation only standard emission values are used.
                        </div>
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
        filters = {
            year: cbam.fe.create_filter('Year', 'Select', 'year', '#filter-section-group-1', []),
            cbam_report: cbam.fe.create_filter('CBAM Report', 'MultiSelectList', 'cbam_report', '#filter-section-group-1', []),
        };

        // Fetch CBAM Report options - respect selected year
        filters.cbam_report.df.get_data = function(txt) {
            const selectedYear = filters.year ? filters.year.get_value() : null;
            let filters_list = [];
            
            // Add year filter if year is selected
            if (selectedYear) {
                filters_list.push(['from_date', '>=', `${selectedYear}-01-01`]);
                filters_list.push(['to_date', '<=', `${selectedYear}-12-31`]);
            }
            
            // Add text search filter if provided
            if (txt) {
                filters_list.push(['report_id', 'like', `%${txt}%`]);
            }
            
            return frappe.db.get_list('CBAM Report', {
                fields: ['name as value', 'report_id as description'],
                filters: filters_list,
                limit: 20,
            });
        };

        // Custom width for Year and CBAM Report filters - make them wider
        setTimeout(() => {
            // Adjust Year filter width (first filter)
            const yearContainer = $('#filter-section-group-1 .frappe-control').first();
            if (yearContainer.length > 0) {
                yearContainer.closest('.col-3').removeClass('col-3').addClass('col-4');
            }
            
            // Adjust CBAM Report filter width (second filter) - make it wider
            const cbamReportContainer = $('#filter-section-group-1 .frappe-control').eq(1);
            if (cbamReportContainer.length > 0) {
                cbamReportContainer.closest('.col-3').removeClass('col-3').addClass('col-8');
            }
        }, 100);

        // Populate year filter with available years from CBAM reports
        populate_year_filter(filters.year);

        // Dynamic event: reload table/chart on change
        filters.year.df.onchange = function() {
            const selectedYear = filters.year.get_value();
            if (selectedYear) {
                // Fetch CBAM reports for the selected year
                frappe.call({
                    method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_cbam_reports_by_year',
                    args: { year: selectedYear },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            // Set all CBAM reports for the selected year
                            filters.cbam_report.set_value(r.message);
                            // Reload table and chart
                            start = 0;
                            all_data = [];
                            page_length = 50;
                            load_report_table(true);
                        } else {
                            // No reports for selected year, clear CBAM report filter
                            filters.cbam_report.set_value([]);
                            // Clear table and chart
                            $('#table-section').html('<div class="text-center text-muted p-4">No CBAM reports found for the selected year.</div>');
                            $('#chart-section').html('<div class="text-center text-muted p-4">No chart data available for the selected year.</div>');
                            $('#pagination-controls').remove();
                        }
                    }
                });
            } else {
                // No year selected, clear CBAM report filter and data
                filters.cbam_report.set_value([]);
                $('#table-section').html('<div class="text-center text-muted p-4">Please select a year to view CBAM reports.</div>');
                $('#chart-section').html('<div class="text-center text-muted p-4">Please select a year to view chart data.</div>');
                $('#pagination-controls').remove();
            }
        };

        filters.cbam_report.df.onchange = function() {
            start = 0;
            all_data = [];
            page_length = 50;
            load_report_table(true);
        };


        return filters;
    }

    /**
     * Populate the year filter with available years from CBAM reports
     * @param {Object} yearFilter - The year filter control
     */
    function populate_year_filter(yearFilter) {
        frappe.call({
            method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_available_years',
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    // Set the options for the Select field
                    yearFilter.df.options = r.message;
                    
                    // Refresh the filter
                    yearFilter.refresh();
                    
                    // Set default value to current year if available, otherwise first available year
                    const currentYear = new Date().getFullYear();
                    const availableYears = r.message;
                    
                    if (availableYears.includes(currentYear)) {
                        yearFilter.set_value(currentYear);
                        // Trigger initial data load after year is set
                        setTimeout(() => trigger_initial_data_load(), 100);
                    } else if (availableYears.length > 0) {
                        yearFilter.set_value(availableYears[0]);
                        // Trigger initial data load after year is set
                        setTimeout(() => trigger_initial_data_load(), 100);
                    }
                } else {
                    // Fallback to current year
                    const currentYear = new Date().getFullYear();
                    yearFilter.df.options = [currentYear];
                    yearFilter.refresh();
                    yearFilter.set_value(currentYear);
                    // Trigger initial data load after year is set
                    setTimeout(() => trigger_initial_data_load(), 100);
                }
            },
            error: function(err) {
                // Fallback to current year
                const currentYear = new Date().getFullYear();
                yearFilter.df.options = [currentYear];
                yearFilter.refresh();
                yearFilter.set_value(currentYear);
                // Trigger initial data load after year is set
                setTimeout(() => trigger_initial_data_load(), 100);
            }
        });
    }

    /**
     * Trigger initial data load after year filter is set up
     * This ensures we respect the year filter from the start
     */
    function trigger_initial_data_load() {
        const selectedYear = filters.year.get_value();
        if (selectedYear) {
            // Fetch CBAM reports for the selected year and load data
            frappe.call({
                method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_cbam_reports_by_year',
                args: { year: selectedYear },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        // Set CBAM reports for the selected year
                        filters.cbam_report.set_value(r.message);
                        // Load data for these reports
                        start = 0;
                        all_data = [];
                        page_length = 50;
                        load_report_table(true);
                    }
                }
            });
        }
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
            method: 'cbam.cbam.page.financial_exposure_forecast.financial_exposure_forecast.get_cbam_report_data',
            args: {
                cbam_reports: selected_reports,
                start,
                page_length,
                year: filters.year ? filters.year.get_value() : null // Don't default to current year for now
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
                    load_highcharts(() => render_chart(chart_data, filters.year ? filters.year.get_value() : null));
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

    function render_chart(chart_data, selectedYear) {
        // Remove any existing toggle switch to prevent duplicates
        $('.tooltip-toggle-container').remove();
        
        // Set default view to 'both' - no toggle switch needed
        let currentTooltipView = 'both'; // Always show both views
        
        // Extract and prepare categories
        let categories = chart_data.categories || [];
        let yearDueDatesMap = chart_data.year_due_dates || {};
        const actualData = chart_data.series[0]?.data || [];
        const forecastData = chart_data.series[1]?.data || [];

        // First calculate basic accumulated exposure for mapping
        const accumulatedExposureBasic = [];
        let cumulative = 0;
        for (let i = 0; i < categories.length; i++) {
            const value = actualData[i] ?? forecastData[i];
            if (value !== null && value !== undefined) {
                cumulative += value;
            }
            accumulatedExposureBasic.push(cumulative);
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

        // Generate monthly categories for ALL years including future years
        const allYears = categories.map(cat => parseInt(cat.match(/\b(\d{4})\b/)[1])).filter(Boolean);
        const minYear = Math.min(...allYears);
        
        // Find the latest due date to ensure categories include it
        const allDueDates = Object.values(yearDueDatesMap).map(dateStr => new Date(dateStr));
        const latestDueDate = allDueDates.length > 0 ? new Date(Math.max(...allDueDates.map(d => d.getTime()))) : null;
        
        // Use the maximum of data years or due date year to ensure due date lines are visible
        const maxYear = latestDueDate ? Math.max(Math.max(...allYears), latestDueDate.getFullYear()) : Math.max(...allYears);
        
        const monthCategories = [];
        for (let year = minYear; year <= maxYear; year++) {
            for (let m = 0; m < 12; m++) {
                const date = new Date(year, m, 1);
                
                // If we have a latest due date, stop generating categories after that month
                if (latestDueDate && date > latestDueDate) {
                    break;
                }
                
                const label = date.toLocaleString('default', { month: 'short' }) + ' ' + year;
                monthCategories.push(label);
            }
            
            // If we've reached the due date, break out of the year loop too
            if (latestDueDate && year === latestDueDate.getFullYear()) {
                break;
            }
        }
        categories = monthCategories;

        // Remap all data series to only appear at quarter-ends
        const actualDataMonth = mapDataToMonths(actualData, categories, chart_data.categories || []);
        const forecastDataMonth = mapDataToMonths(forecastData, categories, chart_data.categories || []);
        const minRequiredActualMonth = mapDataToMonths(minRequiredActual, categories, chart_data.categories || []);
        const minRequiredForecastMonth = mapDataToMonths(minRequiredForecast, categories, chart_data.categories || []);
        const accumulatedExposureBasicMonth = mapDataToMonths(accumulatedExposureBasic, categories, chart_data.categories || []);
        

        
        // Now filter accumulated exposure to only show in December months (end of year)
        // This creates a clean chart that shows yearly progression at key milestones
        const accumulatedExposureMonth = [];
        const currentYear = new Date().getFullYear();
        
        for (let i = 0; i < categories.length; i++) {
            const category = categories[i];
            const monthMatch = category.match(/^(\w+)/);
            const yearMatch = category.match(/\b(\d{4})\b/);
            const year = yearMatch ? parseInt(yearMatch[1]) : null;
            
            if (monthMatch) {
                const month = monthMatch[1].toLowerCase();
                const isDecember = month === 'dec';
                
                if (isDecember) {
                    if (accumulatedExposureBasicMonth[i] !== null && accumulatedExposureBasicMonth[i] !== undefined) {
                        accumulatedExposureMonth.push(accumulatedExposureBasicMonth[i]);
                    } else if (year && year > currentYear) {
                        // For future years, use a forecast value based on current year's accumulated exposure
                        const currentYearValue = accumulatedExposureMonth.find((val, idx) => {
                            const cat = categories[idx];
                            const catYearMatch = cat.match(/\b(\d{4})\b/);
                            const catYear = catYearMatch ? parseInt(catYearMatch[1]) : null;
                            return catYear === currentYear && val !== null;
                        });
                        
                        if (currentYearValue !== undefined) {
                            // Use current year value as base for future forecast
                            accumulatedExposureMonth.push(currentYearValue * 1.1); // 10% increase as forecast
                        } else {
                            // Fallback to default forecast value
                            accumulatedExposureMonth.push(50000);
                        }
                    } else {
                        accumulatedExposureMonth.push(null);
                    }
                } else {
                    accumulatedExposureMonth.push(null); // No data for non-December months
                }
            } else {
                accumulatedExposureMonth.push(null);
            }
        }

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
        
        // Plot a vertical line for every reporting year at its due date
        // Show due lines based on the selected year filter, not current calendar year
        const selectedYearForLines = selectedYear ? parseInt(selectedYear) : new Date().getFullYear();
        
        const plotLines = Object.entries(yearDueDatesMap)
            .filter(([reportingYear, dueDateRaw]) => {
                // Show due lines for future years only, hide current and past years
                const dueDate = new Date(dueDateRaw);
                const dueYear = dueDate.getFullYear();
                const reportingYearInt = parseInt(reportingYear);
                // Only show due lines for future years (after the selected year)
                // Hide due lines for current and past years
                return reportingYearInt > selectedYearForLines;
            })
            .map(([reportingYear, dueDateRaw]) => {
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
            
            // Use the reporting year directly in the label to avoid confusion
            const labelText = `CBAM Certificate cost  ${reportingYear - 1} due: ${formatDueDate(dueDateRaw)}`;
            return {
                value: idx,
                color: '#ff0000',
                width: 2,
                dashStyle: 'Dash',
                label: {
                    text: labelText,
                    rotation: 270, // vertical label
                    x: 20,         // horizontal gap from the line
                    y: 200,        // negative value to center vertically on the line
                    style: { color: '#ff0000', fontWeight: 'bold' },
                    align: 'center'
                },
                zIndex: 5
            };
        });

        // Add a line from December of the previous year to the due date, and a diamond at the due date
        const extraLineSeries = [];
        const extraDiamondSeries = [];
        let isFirstCertificateLine = true; // Track if this is the first line for legend purposes
        
        Object.entries(yearDueDatesMap)
            .filter(([reportingYear, dueDateRaw]) => {
                // Show due lines for future years only, hide current and past years
                const dueDate = new Date(dueDateRaw);
                const dueYear = dueDate.getFullYear();
                const reportingYearInt = parseInt(reportingYear);
                // Only show due lines for future years (after the selected year)
                // Hide due lines for current and past years
                return reportingYearInt > selectedYearForLines;
            })
            .forEach(([reportingYear, dueDateRaw]) => {
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

            // If no value found for previous year, try to find any available value for future year calculations
            if (value === null) {
                // Look for any non-null accumulated exposure value to use as a base
                for (let i = 0; i < accumulatedExposureMonth.length; i++) {
                    if (accumulatedExposureMonth[i] !== null) {
                        value = accumulatedExposureMonth[i];
                        break;
                    }
                }
                
                // If still no value, use a default forecast value for future years
                if (value === null) {
                    value = 50000; // Default forecast value for future years
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
                    name: 'Certificate Submission Period',
                    type: 'line',
                    color: 'green', // green color
                    lineWidth: 3,
                    dashStyle: 'Solid', // solid line
                    marker: { enabled: false },
                    data: [
                        [decIdx, value],
                        [dueIdx, value]
                    ],
                    enableMouseTracking: false,
                    showInLegend: isFirstCertificateLine, // Only show first line in legend
                    zIndex: 2
                });
                
                isFirstCertificateLine = false; // Subsequent lines won't show in legend
                // Add the diamond at the due date
                extraDiamondSeries.push({
                    name: `Forecast total cost Due`,
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
                    enableMouseTracking: true, // Enable tooltips for diamond markers
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
                // Only show columns for current/past years, not for future years
                ...(() => {
                    const currentYear = new Date().getFullYear();
                    // Filter data to only show columns for current/past years
                    const actualDataFiltered = actualDataMonth.map((value, index) => {
                        const category = categories[index];
                        const yearMatch = category?.match(/\b(\d{4})\b/);
                        const dataYear = yearMatch ? parseInt(yearMatch[1]) : null;
                        return (dataYear && dataYear <= currentYear) ? value : null;
                    });
                    
                    const forecastDataFiltered = forecastDataMonth.map((value, index) => {
                        const category = categories[index];
                        const yearMatch = category?.match(/\b(\d{4})\b/);
                        const dataYear = yearMatch ? parseInt(yearMatch[1]) : null;
                        return (dataYear && dataYear <= currentYear) ? value : null;
                    });
                    
                    return [
                        {
                            name: 'Quarterly Financial Exposure Based on Real Data',
                            data: actualDataFiltered,
                            color: '#003366',
                            type: 'column',
                            zIndex: 2
                        },
                        {
                            name: 'Quarterly Financial Exposure Based on Forecasts',
                            data: forecastDataFiltered,
                            color: '#87ceeb',
                            type: 'column',
                            borderColor: '#5fa7c6',
                            borderWidth: 2,
                            zIndex: 2
                        }
                    ];
                })(),
                // Accumulated exposure series - only shows in December (end of year)
                // Data labels display the forecast total cost values for end-of-year costs
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
                    showInLegend: true,
                    zIndex: 1,
                    dataLabels: {
                        enabled: true,
                        format: '€{y:,.0f}',
                        style: {
                            fontSize: '12px',
                            color: 'red'
                        },
                        y: -10
                    }
                },
                // Hide diamonds for future years - only show for current/past years
                ...(() => {
                    const currentYear = new Date().getFullYear();
                    // Filter data to only show diamonds for current/past years
                    const minRequiredActualFiltered = minRequiredActualMonth.map((value, index) => {
                        const category = categories[index];
                        const yearMatch = category?.match(/\b(\d{4})\b/);
                        const dataYear = yearMatch ? parseInt(yearMatch[1]) : null;
                        return (dataYear && dataYear <= currentYear) ? value : null;
                    });
                    
                    const minRequiredForecastFiltered = minRequiredForecastMonth.map((value, index) => {
                        const category = categories[index];
                        const yearMatch = category?.match(/\b(\d{4})\b/);
                        const dataYear = yearMatch ? parseInt(yearMatch[1]) : null;
                        return (dataYear && dataYear <= currentYear) ? value : null;
                    });
                    
                    return [
                        {
                            name: 'Minimum Required Account Balance',
                            data: minRequiredActualFiltered,
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
                            data: minRequiredForecastFiltered,
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
                        }
                    ];
                })(),
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
                    
                    // Build tooltip content - always show both views since toggle is removed
                    let tooltipContent = '';
                    
                    // Always show both Amount Due and Required Certificates (currentTooltipView is set to 'both')
                    tooltipContent = `
                        <span style=\"color:${this.color}\">●</span> ${seriesLabel}: <b>${costDisplay}</b>${certText}`;
                    
                    return tooltipContent;
                }
            },
            legend: {
                enabled: true,
                useHTML: false,
                symbolWidth: 20,
                symbolHeight: 12,
                itemStyle: {
                    fontSize: '12px'
                }
            }
        });
        
        // Populate annual exposure stat cards
        populateAnnualExposureCards(accumulatedExposureMonth, categories);
    }
    
    // Function to populate annual exposure stat cards
    function populateAnnualExposureCards(accumulatedExposureMonth, categories) {
        const cardsContainer = $('#annual-exposure-cards');
        cardsContainer.empty();
        
        // Group accumulated exposure by year
        const yearlyExposure = {};
        
        categories.forEach((category, index) => {
            const yearMatch = category.match(/\b(\d{4})\b/);
            if (yearMatch) {
                const year = yearMatch[1];
                const exposureValue = accumulatedExposureMonth[index];
                
                if (exposureValue !== null && exposureValue !== undefined) {
                    // Use the highest value for each year (usually December)
                    if (!yearlyExposure[year] || exposureValue > yearlyExposure[year]) {
                        yearlyExposure[year] = exposureValue;
                    }
                }
            }
        });
        
        // Create stat cards for each year
        Object.keys(yearlyExposure)
            .sort((a, b) => parseInt(a) - parseInt(b))
            .forEach(year => {
                const exposureValue = yearlyExposure[year];
                const formattedValue = new Intl.NumberFormat('de-DE', {
                    style: 'currency',
                    currency: 'EUR',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                }).format(exposureValue);
                
                const cardHtml = `
                    <div class="flex-shrink-0 me-3 mb-3" style="min-width: 160px; max-width: 200px;">
                        <div class="frappe-card p-2 text-center" style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; height: 55px;">
                            <div class="d-flex flex-column justify-content-center h-100">
                                <div style="font-weight: 500; font-size: 0.8em; color: #6c757d; line-height: 1; margin-bottom: 2px;">
                                    Financial Exposure ${year} (€)
                                </div>
                                <div style="font-weight: 700; font-size: 1em; color: #495057; line-height: 1;">
                                    ${formattedValue}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                cardsContainer.append(cardHtml);
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
