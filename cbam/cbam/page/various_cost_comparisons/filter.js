frappe.provide('cbam');
 
/**
 * Create a filter control and append to the parent selector.
 */
cbam.create_filter = function(label, fieldtype, fieldname, parentSelector, options = null, link_to = null, default_val = null) {
    const df = { label, fieldname, fieldtype, options, default: default_val };
    if (link_to) df.options = link_to;
    const control = frappe.ui.form.make_control({ parent: $('<div class="col mb-2"></div>').appendTo(parentSelector), df });
    control.refresh();
    if (default_val !== undefined && default_val !== null && default_val !== "") {
        control.set_value(default_val);
    }
    return control;
};

/**
 * Setup clear buttons for filter groups.
 */
cbam.setup_filter_clear_buttons = function(filters, load_report_table) {
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
};

/**
 * Setup listeners for filter changes.
 */
cbam.setup_filter_listeners = function(filters, load_report_table, update_stat_card_values, refresh_ets_price_options) {
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
};

/**
 * Utility to collect all selected filters and stat values from the DOM.
 */
cbam.get_all_selected_filters = function(filters) {
    const selected_filters = {};
            ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
                selected_filters[key] = filters[key]?.get_value?.() || [];
            });
            ['ets_price_type', 'year', 'ets_price'].forEach(key => {
                selected_filters[key] = filters[key]?.get_value?.() || '';
            });
            // Special handling for CBAM Factor - use data-original-value if available
            let cbamFactorElement = $('[data-stat="cbam-factor"]');
            let cbamFactor = 0;
            if (cbamFactorElement.attr('data-original-value')) {
                cbamFactor = parseFloat(cbamFactorElement.attr('data-original-value')) || 0;
            } else {
                cbamFactor = parseFloat(cbamFactorElement.text()) || 0;
            }
            selected_filters.cbam_factor = cbamFactor;
            selected_filters.bench_mark = parseFloat($('[data-stat="bench-mark-emission-value"]').text()) || 0;
            selected_filters.emission_value = parseFloat($('[data-stat="standard-emission-value"]').text()) || 0;
            selected_filters.ets_price_value = parseFloat($('[data-stat="ets-price"]').text()) || 0;
            return selected_filters;
};

/**
 * Refresh ETS Price options based on type and year.
 */
cbam.refresh_ets_price_options = function(filters, ets_price_type, year) {
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
};