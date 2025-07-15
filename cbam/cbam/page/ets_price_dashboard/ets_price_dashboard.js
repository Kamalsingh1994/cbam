frappe.pages['ets-price-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'ETS Price Dashboard',
        single_column: true
    });

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
			
			<div class="col-md-2 col-sm-6">
				<label for="date-field-select" class="form-label">Filter by</label>
				<select id="date-field-select" class="form-select form-select-sm input-with-feedback form-control">
					<option value="all"></option>
					<option value="price_date">Price Date</option>
					<option value="creation_date">Creation Date</option>
				</select>
			</div>

			<div class="col-md-3 col-sm-6">
				<label for="from-date" class="form-label">From Date</label>
				<input type="date" class="form-control form-control-sm" id="from-date" />
			</div>

			<div class="col-md-3 col-sm-6">
				<label for="to-date" class="form-label">To Date</label>
				<input type="date" class="form-control form-control-sm" id="to-date" />
			</div>

			<div class="col-md-4 col-sm-12">
				
				<div id="ets-price-type-filter-container" style="margin-bottom: -15px;"></div>
			</div>

			</div>
 		 </div>	

    <div id="chart-section" class="frappe-card mb-4 p-3">
        <button id="reset-zoom-btn" class="btn btn-secondary btn-sm mb-2" style="padding: 2px 6px; font-size: 0.8em; line-height: 1.2;">Reset</button>
        <div id="chart-scroll-wrapper" style="overflow-x: auto; width: 100%; margin-bottom:-12px">
            <div id="ets-price-chart" style="min-width: 1800px;"></div>
        </div>
    </div>
    <div id="ets-price-table-section"></div>
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

    function renderPaginationControls(dataArg) {
        const data = dataArg || allData;
        $('#pagination-controls').remove();
        const showing_from = data.length === 0 ? 0 : 1;
        const showing_to = data.length;
        const isFiltered = data.length !== allData.length;
        const html = `
            <div id="pagination-controls" class="cbam-pagination-footer d-flex flex-wrap align-items-center justify-content-between mt-2">
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
                    <button id="load-more" class="btn btn-primary btn-sm px-2" ${(isFiltered || data.length >= total_count) ? 'disabled' : ''}>Load More</button>
                </div>
            </div>
        `;
        $('#ets-price-table-section').after(html);
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
        const dateField = $('#date-field-select').val() || 'price_date';
        const fromDate = $('#from-date').val();
        const toDate = $('#to-date').val();
        const etsTypes = etsPriceTypeFilter.get_value() || [];
        const filtered = allData.filter(row => {
            let pass = true;
            if (dateField === 'all' || !dateField) {
                // Show if either date is in range (or if no date filters are set)
                let priceDate = row.price_date ? row.price_date.split(' ')[0] : '';
                let creationDate = row.creation_date ? row.creation_date.split(' ')[0] : '';
                let inRange = false;
                if (fromDate || toDate) {
                    if (fromDate && priceDate >= fromDate && (!toDate || priceDate <= toDate)) inRange = true;
                    if (fromDate && creationDate >= fromDate && (!toDate || creationDate <= toDate)) inRange = true;
                    if (toDate && priceDate <= toDate && (!fromDate || priceDate >= fromDate)) inRange = true;
                    if (toDate && creationDate <= toDate && (!fromDate || creationDate >= fromDate)) inRange = true;
                    pass = inRange;
                }
                // If no from/to date, show all
            } else {
                let dateValue = row[dateField];
                if (!dateValue) return false;
                dateValue = dateValue.split(' ')[0];
                if (fromDate && dateValue < fromDate) pass = false;
                if (toDate && dateValue > toDate) pass = false;
            }
            if (etsTypes.length && !etsTypes.includes(row.ets_price_type)) pass = false;
            return pass;
        });
        lastFilteredData = filtered;
        renderChart(filtered);
        renderTable(filtered);
    }

    // Filter on change for all filter controls
    $('#date-field-select, #from-date, #to-date').on('change', applyFilters);
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
            datatable = new DataTable('#ets-price-table-section', {
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
                    const priceYear = originalRow ? originalRow.price_year : '';
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

    // Populate ETS Price Type options
    function populateEtsPriceTypeOptions(data) {
        const types = [...new Set(data.map(row => row.ets_price_type).filter(Boolean))];
        etsPriceTypeFilter.df.options = types.map(type => ({ value: type, description: type }));
        etsPriceTypeFilter.refresh();
    }

    // Initial load
    fetchData(true);
};