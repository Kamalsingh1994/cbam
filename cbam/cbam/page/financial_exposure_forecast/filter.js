frappe.provide('cbam.fe');

/**
 * Create a filter control and append to the parent selector.
 */
cbam.fe.create_filter = function(label, fieldtype, fieldname, parentSelector, options = null, link_to = null, default_val = null) {
    const df = { label, fieldname, fieldtype, options, default: default_val };
    if (link_to) df.options = link_to;
    
    // Determine appropriate column class based on parent selector
    let columnClass = 'col mb-2';
    if (parentSelector === '#filter-section-group-2') {
        // For group 2 (Year, ETS Price Type) - use smaller width to prevent overlap
        columnClass = 'col-4 mb-2';
    } else if (parentSelector === '#filter-section-group-1') {
        // For group 1 (CN Code, Supplier, Article Number, Reporting Period) - use compact width for one line
        columnClass = 'col-3 mb-2';
    }
    
    const control = frappe.ui.form.make_control({ parent: $('<div class="' + columnClass + '"></div>').appendTo(parentSelector), df });
    control.refresh();
    if (default_val !== undefined && default_val !== null && default_val !== "") {
        control.set_value(default_val);
    }
    return control;
};

/**
 * Setup clear buttons for filter groups.
 */
cbam.fe.setup_filter_clear_buttons = function(filters, load_report_table) {
    $('#clear-group-1').on('click', () => {
        ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
            filters[key]?.set_value([]);
        });
        load_report_table(true);
    });
    $('#clear-group-2').on('click', () => {
        ['ets_price_type', 'year', 'month'].forEach(key => {
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
cbam.fe.setup_filter_listeners = function(filters, load_report_table, update_stat_card_values, refresh_ets_price_options) {
    // Group 1 filters - only trigger table reload
    ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
        const ctrl = filters[key];
        if (ctrl) {
            ctrl.df.onchange = () => {
                load_report_table(true);
            };
        }
    });
    
    // Group 2 filters - trigger stat card updates and ETS price refresh
    ['ets_price_type', 'year', 'month'].forEach(key => {
        const ctrl = filters[key];
        if (ctrl) {
            ctrl.df.onchange = () => {
                const selected_filters = {
                    ets_price_type: filters.ets_price_type.get_value(),
                    year: filters.year.get_value(),
                };
                
                // Update stat cards
                update_stat_card_values(key, selected_filters);
                
                // Refresh ETS price if relevant filters changed
                if (key === 'ets_price_type' || key === 'year') {
                    refresh_ets_price_options(
                        filters.ets_price_type.get_value(),
                        filters.year.get_value()
                    );
                }
                
                // Reload table
                load_report_table(true);
            };
        }
    });
};

/**
 * Utility to collect all selected filters and stat values from the DOM.
 */
cbam.fe.get_all_selected_filters = function(filters) {
    const selected_filters = {};
    
    // Collect filter values
    ['cn_code', 'supplier', 'article_number', 'reporting_period'].forEach(key => {
        selected_filters[key] = filters[key]?.get_value?.() || [];
    });
    
    ['ets_price_type', 'year'].forEach(key => {
        const value = filters[key]?.get_value?.();
        selected_filters[key] = value || '';
    });
    
    // Get ETS Price value from the stat card display
    const etsPriceValue = cbam.get_ets_price_from_stat_card();
    selected_filters.ets_price = etsPriceValue;
    
    // Get other stat values
    selected_filters.cbam_factor = cbam.get_stat_value('cbam-factor', true);
    
    // Get bench_mark and emission_value from backend since stat cards were removed
    // These will be fetched by the backend when get_report_data is called
    selected_filters.bench_mark = 0.0; // Will be fetched from backend
    selected_filters.emission_value = 0.0; // Will be fetched from backend
    selected_filters.ets_price_value = etsPriceValue;
    
    return selected_filters;
};

/**
 * Get ETS Price value from stat card with proper parsing.
 */
cbam.fe.get_ets_price_from_stat_card = function() {
    const etsPriceElements = $('[data-stat="ets-price"]');
    
    let finalValue = 0.0;
    etsPriceElements.each(function(index) {
        const element = $(this);
        const elementText = element.text();
        
        if (index === 0) { // Use the first element for the actual value
            if (!elementText || elementText === '--') {
                finalValue = 0.0;
            } else {
                // Parse numeric value, removing Euro symbol if present
                const cleanText = elementText.replace('€', '').trim();
                finalValue = parseFloat(cleanText) || 0.0;
            }
        }
    });
    
    return finalValue;
};

/**
 * Get stat value from DOM with proper parsing.
 */
cbam.fe.get_stat_value = function(statName, useOriginalValue = false) {
    const element = $(`[data-stat="${statName}"]`);
    if (!element.length) return 0.0;
    
    if (useOriginalValue && element.attr('data-original-value')) {
        return parseFloat(element.attr('data-original-value')) || 0.0;
    }
    
    return parseFloat(element.text()) || 0.0;
};

/**
 * Update ETS Price stat card with new value.
 */
cbam.fe.update_ets_price_stat_card = function(displayValue) {
    const selectors = [
        '[data-stat="ets-price"]',
        '.stat-value[data-stat="ets-price"]'
    ];
    
    selectors.forEach(selector => {
        const elements = $(selector);
        if (elements.length > 0) {
            elements.each(function() {
                $(this).text(displayValue);
            });
        }
    });
};

/**
 * Refresh ETS Price options based on type and year.
 */
cbam.fe.refresh_ets_price_options = function(filters, ets_price_type, year) {
    if (!ets_price_type || !year) {
        return;
    }
    
    // Fetch latest price for the selected year and type
    frappe.call({
        method: 'cbam.cbam.page.various_cost_comparisons.various_cost_comparisons.get_latest_ets_price',
        args: { year: year, ets_price_type: ets_price_type },
        callback: function(r) {
            if (r.message) {
                const priceData = r.message;
                const displayValue = `€${priceData.price}`;
                
                // Update the ETS Price stat card
                cbam.update_ets_price_stat_card(displayValue);
            } else {
                cbam.update_ets_price_stat_card('0.0');
            }
        },
        error: function(err) {
            cbam.update_ets_price_stat_card('0.0');
        }
    });
};