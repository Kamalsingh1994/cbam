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
        <div class="d-flex flex-wrap align-items-end gap-2 mb-2" id="ets-filter-row" style="max-width: 1100px;">
            <div class="flex-shrink-0">
                <label for="from-date" class="form-label mb-0" style="font-size:0.95em;">From Date</label>
                <input type="date" class="form-control form-control-sm" id="from-date" style="min-width:140px;">
            </div>
            <div class="flex-shrink-0">
                <label for="to-date" class="form-label mb-0" style="font-size:0.95em;">To Date</label>
                <input type="date" class="form-control form-control-sm" id="to-date" style="min-width:140px;">
            </div>
            <div class="flex-shrink-0" id="ets-price-type-filter-container"></div>
            <div class="ms-auto flex-shrink-0">
                <button id="reset-zoom-btn" class="btn btn-secondary btn-sm mb-1" style="padding:2px 12px; font-size: 0.95em;">Reset Zoom</button>
            </div>
        </div>
        <div id="chart-scroll-wrapper" style="overflow-x: auto; width: 100%; margin-bottom:10px">
            <div id="ets-price-chart" style="min-width: 1800px;"></div>
        </div>
        <div id="ets-price-table-section"></div>
        <style>
            #ets-filter-row .form-label { min-width: 80px; }
            #ets-filter-row .form-control-sm { min-width: 140px; }
            #ets-filter-row > div { margin-bottom: 0 !important; }
            #ets-price-type-filter-container .control-input-wrapper { min-width: 200px; }
        </style>
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

    function renderPaginationControls() {
        $('#pagination-controls').remove();
        const showing_from = total_count === 0 ? 0 : 1;
        const showing_to = allData.length;
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
                    <button id="load-more" class="btn btn-primary btn-sm px-2" ${(allData.length >= total_count) ? 'disabled' : ''}>Load More</button>
                </div>
            </div>
        `;
        $('#ets-price-table-section').after(html);
        $('#page-length-select').val(page_length);
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

    function applyFilters() {
        const fromDate = $('#from-date').val();
        const toDate = $('#to-date').val();
        const etsTypes = etsPriceTypeFilter.get_value() || [];
        const filtered = allData.filter(row => {
            let pass = true;
            if (fromDate && row.price_date < fromDate) pass = false;
            if (toDate && row.price_date > toDate) pass = false;
            if (etsTypes.length && !etsTypes.includes(row.ets_price_type)) pass = false;
            return pass;
        });
        renderChart(filtered);
    }

    // Filter on change for all filter controls
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
                    total_count = r.message.total_count || 0;
                    if (reset) {
                        allData = r.message.data || [];
                    } else {
                        allData = allData.concat(r.message.data || []);
                    }
                    populateEtsPriceTypeOptions(allData);
                    renderTable(allData);
                    renderChart(allData);
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
            { id: 'creation_date', name: 'Creation Date', width: 200 },
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
            bindDatatableSelectionEvents();
        } else {
            datatable.refresh(tableData);
        }
        renderPaginationControls(); // <-- Always call here after table is rendered
    }

    function bindDatatableSelectionEvents() {
        if (!datatable) return;
        datatable.on('onCheckRow', function() {
            // Optionally update chart with only selected rows
            // const selectedData = getSelectedRowsData();
            // renderChart(selectedData);
        });
        datatable.on('onUncheckRow', function() {
            // Optionally update chart with only selected rows
            // const selectedData = getSelectedRowsData();
            // renderChart(selectedData);
        });
    }

    function getSelectedRowsData() {
        if (!datatable) return [];
        const selectedIndexes = datatable.rowmanager.getCheckedRows();
        return selectedIndexes.map(idx => allData[idx]);
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
        console.log('Rendering chart with data:', chartData);
        console.log('Chart container exists:', !!document.getElementById('ets-price-chart'));
        if (!document.getElementById('ets-price-chart')) {
            console.error('Chart container missing!');
            return;
        }
        if (typeof Highcharts === 'undefined') {
            $('#ets-price-chart').html('<div class="text-muted p-4">Loading chart library...</div>');
            return;
        }
        if (chartData.length === 0) {
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
                        new Date(row.price_date).getTime() === point.x &&
                        Number(row.price) === point.y
                    );
                    const priceYear = originalRow ? originalRow.price_year : '';
                    return `<b>Date:</b> ${Highcharts.dateFormat('%Y-%m-%d', point.x)}<br/>
                            <b>Price:</b> ${point.y}<br/>
                            <b>Price Year:</b> ${priceYear}`;
                }
            },
            series: [
                {
                    name: 'ETS Price',
                    data: chartData,
                    type: 'line',
                    color: '#007bff',
                    marker: { enabled: true }
                },
                ...avgYearSeries
            ],
            credits: { enabled: false }
        });
    }

    // Add event handler for custom Reset Zoom button
    $('#reset-zoom-btn').on('click', function() {
        renderChart(allData);
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