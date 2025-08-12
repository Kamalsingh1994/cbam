frappe.provide('cbam')


// Helper: Get chart data, optionally per tonne
cbam.get_chart_data = function get_chart_data(data, per_tonne = false) {
    const labels = [];
    const actual_costs = [];
    const standard_costs = [];
    if (!data) return { labels: [], actual_costs: [], standard_costs: [] };
    data.forEach(row => {
        const article = row.article_number || '';
        const supplier = row.supplier || '';
        labels.push(`${article} (${supplier})`);
        let mass = Number(row.raw_mass) || 0;
        let actual = Number(row.real_emission_cost) || 0;
        let standard = Number(row.standard_emission_cost) || 0;
        if (per_tonne && mass > 0) {
            let mass_tonnes = mass / 1000;
            actual = actual / mass_tonnes;
            standard = standard / mass_tonnes;
        }
        actual_costs.push(actual);
        standard_costs.push(standard);
    });
    return {
        labels,
        actual_costs,
        standard_costs
    };
}


cbam.update_chart = function update_chart(chart_data) {
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
    //const minWidth = Math.max(600, labels.length * 80); // 80px per label as a heuristic
    //$('#chart-section').append('<div id="highchart-scroll-inner" style="overflow-x: auto; width: 100%;"><div id="highchart-bar" style="min-width: ' + minWidth + 'px; max-height: 350px;"></div></div>');

    // Highcharts integration: create chart div without scroll
    $('#chart-section').append('<div id="highchart-bar" style="width: 100%; height: 350px;"></div>');

    function renderHighChart() {
        Highcharts.chart('highchart-bar', {
            chart: {
                type: 'column',
                height: 350,
                zoomType: 'x'
            },
            credits: {
                enabled: false
            },
            title: { text: __('Cost Exposure of Articles @ [selected ETS Price basis]') },
            xAxis: {
                categories: labels,
                labels: {
                    rotation: 45,
                    style: { fontSize: '12px' }
                }
            },
            yAxis: {
                title: { text: __('Costs [€]') },
                min: 0
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