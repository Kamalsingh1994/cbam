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

    // Use chart labels directly
    let labels = chart_data.labels;

    // Create chart div
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
            accessibility: { enabled: false },
            title: { text: __('Cost Exposure of Articles @ [selected ETS Price basis]') },
            xAxis: {
                categories: labels,
                labels: {
                    rotation: 45,
                    style: { fontSize: '12px' }
                }
            },
            yAxis: {
                title: { text: __('Cost [€]') },
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

    // Use centralized Highcharts loader to prevent conflicts when navigating between pages
    // With fallback if cbam.utils is not available
    function loadChart() {
        if (typeof cbam !== 'undefined' && typeof cbam.utils !== 'undefined' && typeof cbam.utils.loadHighcharts === 'function') {
            cbam.utils.loadHighcharts((error) => {
                if (error) {
                    console.error('Highcharts load error:', error);
                    $('#chart-section').html('<div class="text-center text-danger p-4">Chart library failed to load. Please refresh the page.</div>');
                } else {
                    renderHighChart();
                }
            });
        } else {
            // Fallback: direct loading if utils not available
            if (typeof window.Highcharts === 'undefined') {
                const script = document.createElement('script');
                script.src = 'https://code.highcharts.com/highcharts.js';
                script.onload = () => renderHighChart();
                script.onerror = () => {
                    $('#chart-section').html('<div class="text-center text-danger p-4">Chart library failed to load. Please refresh the page.</div>');
                };
                document.head.appendChild(script);
            } else {
                renderHighChart();
            }
        }
    }
    
    loadChart();
}