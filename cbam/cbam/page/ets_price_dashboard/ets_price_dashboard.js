frappe.pages['ets-price-dashboard'].on_page_load = function(wrapper) {
    if (!sessionStorage.getItem('ets_price_dashboard_reloaded')) {
        sessionStorage.setItem('ets_price_dashboard_reloaded', '1');
        location.reload();
        return;
    } else {
        sessionStorage.removeItem('ets_price_dashboard_reloaded');
    }
    $(wrapper).empty();
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'ETS Price Dashboard',
        single_column: true
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
    </style>`).appendTo('head');

    // Insert tab navigation just below the page title
    $(page.body).prepend(`
        <ul class="nav nav-tabs mb-3" id="dashboard-tabs">
            <li class="nav-item">
                <a class="nav-link active" href="/app/ets-price-dashboard">ETS Price Dashboard</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="/app/financial-evaluation-report">Financial Evaluation Report</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" href="/app/cbam-report-cost-forecast">CBAM Report Cost Forecast</a>
            </li>
        </ul>
    `);

    // Ensure Highcharts is loaded
    if (typeof Highcharts === 'undefined') {
        var script = document.createElement('script');
        script.src = 'https://code.highcharts.com/highcharts.js';
        script.onload = function() {
            // After loading, re-render chart if data is present
            if (allData && allData.length) renderChart(allData);
        };
        document.head.appendChild(script);
    }

    // Add filter section above the chart
    $(page.body).append(`
        <div class="frappe-card mb-4 p-3" id="ets-filter-section">
			<div class="section-title mb-2" style="font-size: 1.1em; font-weight: 600;">
			Filter Data
			</div>

			<div class="row gx-3 gy-3 align-items-end" style="max-width: 1000px;">
			
			<div class="col-md-3 col-sm-6">
				<label for="from-date" class="form-label">From Date</label>
				<input type="date" class="form-control form-control-sm" id="from-date" />
			</div>

			<div class="col-md-3 col-sm-6">
				<label for="to-date" class="form-label">To Date</label>
				<input type="date" class="form-control form-control-sm" id="to-date" />
			</div>

			<div class="col-md-3 col-sm-12">
				<div id="ets-price-type-filter-container" style="margin-bottom: -15px;"></div>
			</div>

            <div class="col-md-1 col-sm-12 d-flex justify-content-end align-items-end">
                <button id="clear-filters-btn" class="btn btn-secondary btn-sm w-100">Clear</button>
            </div>

			</div>
 		 </div>	

    <div id="chart-section" class="frappe-card mb-4 p-3">
        <button id="reset-zoom-btn" class="btn btn-secondary btn-sm mb-2" style="padding: 2px 6px; font-size: 0.8em; line-height: 1.2;">Reset</button>
        <div id="chart-scroll-wrapper" style="overflow-x: auto; width: 100%; margin-bottom:-12px">
            <div id="ets-price-chart" style="min-width: 1800px;"></div>
        </div>
    </div>
    <div class="frappe-card mb-4" id="table-scroll-container" style="overflow-x: auto;">
        <div id="table-section"></div>
    </div>
    `);

    // Create Frappe MultiSelectList for ETS Price Type (move this up before any usage)
    const etsPriceTypeFilter = frappe.ui.form.make_control({
        parent: $('#ets-price-type-filter-container'),
        df: {
            label: 'ETS Price Type',
            fieldtype: 'MultiSelectList',
            fieldname: 'ets_price_type',
            options: [], // will be set dynamically
            reqd: 0
        },
        render_input: true
    });

    // Table/Chart config
    const doctype = "ETS Carbon Price";
    const fields = [
        "ets_price_type", "carbon_price_source", "price", "price_date", "creation as creation_date", "price_year"
    ];
    let allData = [];
    let start = 0;
    let page_length = 50;
    let total_count = 0;
    let datatable = null;
    let initialFilterApplied = false;
    let lastFilteredData = [];
    let isClearing = false;

    function renderPaginationControls(dataArg) {
        const data = dataArg || allData;
        $('#pagination-controls').remove();
        const showing_from = data.length === 0 ? 0 : 1;
        const showing_to = data.length;
        const isFiltered = data.length !== allData.length;
        const html = `
            <div id="pagination-controls" class="cbam-pagination-footer d-flex flex-wrap align-items-center justify-content-between mt-2 bg-light border rounded" style="padding: 0.75rem 1rem; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <span class="mx-2">Showing <b>${showing_from}&ndash;${showing_to}</b> of <b>${isFiltered ? showing_to : total_count}</b></span>
                    <span class="mx-2">| Rows per load: </span>
                    <select id="page-length-select" class="form-select form-select-sm d-inline-block w-auto" ${isFiltered ? 'disabled' : ''}>
                        <option value="20">20</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="500">500</option>
                    </select>
                </div>
                <div class="ms-auto">
                    <button id="load-more" class="btn btn-primary btn-sm py-1 px-2" style="font-size: 0.85em; min-width: 70px; padding: 2px 8px;" ${(isFiltered || data.length >= total_count) ? 'disabled' : ''}>Load More</button>
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
        $('#table-scroll-container').append(html);
        $('#page-length-select').val(page_length);
        if (!isFiltered) {
            $('#page-length-select').on('change', function () {
                page_length = parseInt($(this).val(), 10);
                start = 0;
                allData = [];
                if (datatable) { datatable.destroy(); datatable = null; }
                fetchData(true);
            });
            $('#load-more').on('click', () => {
                start = allData.length;
                fetchData();
            });
        }
    }

    function applyFilters() {
        const dateField = 'price_date';
        let fromDate = $('#from-date').val();
        let toDate = $('#to-date').val();
        const etsTypes = etsPriceTypeFilter.get_value() || [];

        // No default date logic here; only set on initial page load

        const filtered = allData.filter(row => {
            let pass = true;
            // Always filter by price_date
            let priceDate = row.price_date ? row.price_date.split(' ')[0] : '';
            if (fromDate && priceDate < fromDate) pass = false;
            if (toDate && priceDate > toDate) pass = false;
            if (etsTypes.length && !etsTypes.includes(row.ets_price_type)) pass = false;
            return pass;
        });
        lastFilteredData = filtered;
        console.log("filtered: ", lastFilteredData)
        renderChart(filtered);
        renderTable(filtered);
    }

    // Filter on change for date controls only
    $('#from-date, #to-date').on('change', applyFilters);
    etsPriceTypeFilter.df.onchange = applyFilters;

    function fetchData(reset = false) {
        frappe.call({
            method: "cbam.cbam.page.ets_price_dashboard.ets_price_dashboard.get_table_data",
            args: {
                doctype,
                fields: JSON.stringify(fields),
                start,
                page_length
            },
            callback: function(r) {
                if (r.message) {
                    console.log("data: ", r.message)
                    total_count = r.message.total_count || 0;
                    if (reset) {
                        allData = r.message.data || [];
                    } else {
                        allData = allData.concat(r.message.data || []);
                    }
                    populateEtsPriceTypeOptions(allData);
                    renderTable(allData);
                    renderChart(allData);
                    // Set default dates and apply filter only on first load
                    if (!initialFilterApplied) {
                        const now = new Date();
                        const year = now.getFullYear();
                        const month = now.getMonth();
                        const firstDay = new Date(year, month, 1);
                        const lastDay = new Date(year, month + 1, 0);
                        function formatDateLocal(date) {
                            const y = date.getFullYear();
                            const m = String(date.getMonth() + 1).padStart(2, '0');
                            const d = String(date.getDate()).padStart(2, '0');
                            return `${y}-${m}-${d}`;
                        }
                        $('#from-date').val(formatDateLocal(firstDay));
                        $('#to-date').val(formatDateLocal(lastDay));
                        initialFilterApplied = true;
                        applyFilters();
                    }
                }
            }
        });
    }

    function renderTable(data) {
        const columns = [
            { id: 'ets_price_type', name: 'ETS Price Type', width: 200 },
            { id: 'carbon_price_source', name: 'Carbon Price Source', width: 200 },
            { id: 'price', name: 'Price', width: 200 },
            { id: 'price_date', name: 'Price Date', width: 200 },
            { id: 'creation_date', name: 'Creation Date', width: 212 },
            { id: 'price_year', name: 'Price Year', width: 180 }
        ];
        const tableData = data.map(row => ({
            ...row,
            price: Number(row.price).toFixed(2),
            price_date: row.price_date ? frappe.datetime.str_to_user(row.price_date) : '',
            creation_date: row.creation_date ? frappe.datetime.str_to_user(row.creation_date) : ''
        }));
        if (!datatable) {
            datatable = new DataTable('#table-section', {
                columns,
                data: tableData,
                layout: 'fixed',
                stickyHeader: true,
                scrollY: '400px',
                scrollX: true,
                className: 'frappe-datatable',
                checkboxColumn: true // checklist enabled
            });
        } else {
            datatable.refresh(tableData);
        }
        renderPaginationControls(data); // <-- Always call here after table is rendered
    }

    function getAveragePricePerYearSeries(data) {
        const yearMap = {};
        data.forEach(row => {
            if (!row.price_year) return;
            const year = row.price_year;
            if (!yearMap[year]) yearMap[year] = [];
            if (row.price) yearMap[year].push(Number(row.price));
        });
        // For each year, create two points: Jan 1 and Dec 31, both with the average value
        const avgPoints = Object.entries(yearMap).flatMap(([year, prices]) => {
            const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
            const start = new Date(`${year}-01-01`).getTime();
            const end = new Date(`${year}-12-31`).getTime();
            return [
                [start, avg],
                [end, avg]
            ];
        });
        return [{
            name: 'Avg Price per Year',
            data: avgPoints.sort((a, b) => a[0] - b[0]),
            type: 'line',
            dashStyle: 'ShortDash',
            color: '#FF5733',
            marker: { enabled: false },
            step: 'left'
        }];
    }

    function renderChart(data) {
        // Standard chart data: dated points
        const chartData = data
            .filter(row => row.price_date && row.price)
            .map(row => [
                new Date(row.price_date).getTime(),
                Number(row.price)
            ])
            .sort((a, b) => a[0] - b[0]);
        // Dynamically set min-width for chart container for browser scroll
        const minWidth = Math.max(1800, chartData.length * 60); // 60px per point for clarity
        $('#ets-price-chart').css('min-width', minWidth + 'px');
        const avgYearSeries = getAveragePricePerYearSeries(data);
        // If no dated chart data, but price_year data exists, show average price per year as points
        let series = [];
        if (chartData.length === 0) {
            // Check for price_year data
            const yearMap = {};
            data.forEach(row => {
                if (row.price_year && row.price) {
                    if (!yearMap[row.price_year]) yearMap[row.price_year] = [];
                    yearMap[row.price_year].push(Number(row.price));
                }
            });
            const avgPoints = Object.entries(yearMap).map(([year, prices]) => {
                const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
                // Use Jan 1 of the year for the x-axis
                return [new Date(`${year}-01-01`).getTime(), avg];
            });
            if (avgPoints.length > 0) {
                series = [{
                    name: 'Avg Price per Year',
                    data: avgPoints,
                    type: 'line',
                    color: '#FF5733',
                    marker: { enabled: true },
                    dashStyle: 'ShortDash',
                    step: 'left'
                }];
            }
        } else {
            series = [
                {
                    name: 'ETS Price',
                    data: chartData,
                    type: 'line',
                    color: '#007bff',
                    marker: { enabled: true }
                },
                ...avgYearSeries
            ];
        }
        if (typeof Highcharts === 'undefined') {
            $('#ets-price-chart').html('<div class="text-muted p-4">Loading chart library...</div>');
            return;
        }
        if (series.length === 0 || (series[0].data && series[0].data.length === 0)) {
            $('#ets-price-chart').html('<div class="text-muted p-4">No data for chart</div>');
            return;
        }
        Highcharts.chart('ets-price-chart', {
            chart: {
                type: 'arearange',
                zoomType: 'x'
            },
            title: { text: 'ETS Carbon Price Over Time' },
            xAxis: {
                type: 'datetime',
                title: { text: 'Date' },
                tickInterval: 7 * 24 * 3600 * 1000, // 1 week
                dateTimeLabelFormats: {
                    week: '%e %b, %Y'
                }
            },
            yAxis: { title: { text: 'Price' } },
            tooltip: {
                formatter: function () {
                    const point = this.point;
                    // Find the original data row for this point
                    const originalRow = data.find(row =>
                        (row.price_date && new Date(row.price_date).getTime() === point.x && Number(row.price) === point.y) ||
                        (row.price_year && new Date(`${row.price_year}-01-01`).getTime() === point.x && Number(row.price) === point.y)
                    );
                    let priceYear = originalRow ? originalRow.price_year : '';
                    // Fallback: extract year from price_date if price_year is null
                    if ((!priceYear || priceYear === 'null') && originalRow && originalRow.price_date) {
                        try {
                            priceYear = new Date(originalRow.price_date).getFullYear();
                        } catch (e) {
                            priceYear = '';
                        }
                    }
                    return `<b>Date:</b> ${Highcharts.dateFormat('%Y-%m-%d', point.x)}<br/>
                            <b>Price:</b> ${point.y}<br/>
                            <b>Price Year:</b> ${priceYear}`;
                }
            },
            series: series,
            credits: { enabled: false }
        });
    }

    // Add event handler for custom Reset Zoom button
    $('#reset-zoom-btn').on('click', function() {
        renderChart(lastFilteredData);
    });

    // Add event handler for Clear button
    $(document).on('click', '#clear-filters-btn', function() {
        isClearing = true;
        $('#from-date').val('').trigger('change');
        $('#to-date').val('').trigger('change');
        etsPriceTypeFilter.set_value([]);
        applyFilters();
        setTimeout(() => { isClearing = false; }, 100);
    });

    // Populate ETS Price Type options
    function populateEtsPriceTypeOptions(data) {
        // Get unique types, filter out 'Prediction'
        const types = [...new Set(data.map(row => row.ets_price_type).filter(Boolean))].filter(type => type !== 'Prediction');
        etsPriceTypeFilter.df.options = types.map(type => ({ value: type, description: type }));
        etsPriceTypeFilter.refresh();
    }

    // Initial load
    fetchData(true);
    // Set default dates only on initial page load
    function setDefaultDatesIfEmpty() {
        let fromDate = $('#from-date').val();
        let toDate = $('#to-date').val();
        if (!fromDate || !toDate) {
            const now = new Date();
            const year = now.getFullYear();
            const month = now.getMonth();
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            function formatDateLocal(date) {
                const y = date.getFullYear();
                const m = String(date.getMonth() + 1).padStart(2, '0');
                const d = String(date.getDate()).padStart(2, '0');
                return `${y}-${m}-${d}`;
            }
            $('#from-date').val(formatDateLocal(firstDay));
            $('#to-date').val(formatDateLocal(lastDay));
        }
    }
    setTimeout(setDefaultDatesIfEmpty, 100);
};