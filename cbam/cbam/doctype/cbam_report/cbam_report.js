frappe.ui.form.on('CBAM Report', {
    refresh(frm) {
      if (frm.doc.cbam_report_data?.length > 0) {
        add_import_button_to_child_table(frm);
      }

      disable_imported_rows(frm);
      select_non_imported_rows(frm); // select non-imported rows by default
    },
  
    report_attachment(frm) {
        if (!frm.doc.report_attachment || !frm.doc.name) return;
        frappe.call({
          method: 'cbam.utils.pdf_export.extract_cbam_pdf_flex',
          args: {
            file_url: frm.doc.report_attachment
          },
          callback: function (r) {
            const data = r.message;
            if (Array.isArray(data) && data.length > 0) {
              frm.clear_table('cbam_report_data');
    
              data.forEach(row => {
                frm.add_child('cbam_report_data', {
                  section: row.section,
                  cn_code: row.cn_code,
                  operator_name: row.operator_name,
                  installation_name: row.installation_name,
                  country: row.country_of_production,
                  measurement_unit: row.type_of_measurement_unit,
                  quantity: row.quantity,
                  direct_embedded_emissions: row.specific_direct_embedded_emissions,
                  indirect_embedded_emissions: row.specific_indirect_embedded_emissions,
                  determination_type: row.type_of_determination,
                  requested_procedure_code: row.requested_procedure_code
                });
              });
    
              frm.refresh_field('cbam_report_data');
              disable_imported_rows(frm); // also apply on new data
              select_non_imported_rows(frm); // select non-imported rows by default
            } else {
              frappe.msgprint('No data returned or parsed from file.');
            }
          }
        });
      }
  });
  
  function disable_imported_rows(frm) {
    const grid = frm.fields_dict.cbam_report_data.grid;
      grid.grid_rows.forEach(row => {
        if (row.doc.imported) {
          // Disable the checkbox
          row.wrapper.find('input[type=checkbox]').prop('disabled', true);
        }
      });
  }


  function add_import_button_to_child_table(frm) {
    const grid = frm.get_field('cbam_report_data').grid;
  
    if (grid.custom_import_button_added) return;
  
    // Add Frappe standard-styled button to child table grid footer
    grid.add_custom_button(__('Import External Goods'), () => {
      const selected_rows = grid.get_selected_children().filter(row => !row.imported);
  
      if (!selected_rows.length) {
        frappe.msgprint('Please select one or more rows to import.');
        return;
      }
  
      frappe.call({
        method: 'cbam.cbam.doctype.external_good.external_good.bulk_create_external_goods',
        args: {
          rows: selected_rows,
          declarant: frm.doc.declarant,
        },
        callback: function (r) {
          if (r.message?.created?.length) {
            const created = r.message.created;
  
            created.forEach(item => {
              const row = frm.doc.cbam_report_data.find(r => r.idx === item.idx);
              if (row) {
                row.external_good = item.external_good;
              }
            });
  
            frm.refresh_field('cbam_report_data');
  
            const external_goods = created.map(e => e.external_good);
  
            frappe.msgprint({
              title: __('Success'),
              indicator: 'green',
              message: `
                ${external_goods.length} External Goods created and linked.<br><br>
                <button class="btn btn-sm btn-primary view-external-goods">View External Goods</button>
              `
            });
  
            setTimeout(() => {
              $('.view-external-goods').on('click', function () {
                frappe.set_route('List', 'External Good', {
                  name: ['in', external_goods]
                });
              });
            }, 200);
          } else {
            frappe.msgprint('No records created.');
          }
        }
      });
    });
  
    // Show it only when rows are selected
    grid.wrapper.on('change', 'input[type="checkbox"]', function () {
      const hasSelected = grid.get_selected_children().some(row => !row.imported);
      $btn.toggle(hasSelected);
    });
    
    // Style button after it's rendered
    setTimeout(() => {
        $('.grid-footer .btn:contains("Import External Goods")').css({
          'background-color': '#000',
          'color': '#fff',
        });
    }, 100);

    grid.custom_import_button_added = true;
  }
  
  function select_non_imported_rows(frm) {
    const grid = frm.fields_dict.cbam_report_data.grid;
    grid.grid_rows.forEach(row => {
      if (!row.doc.imported) {
        row.doc.__checked = 1;
        row.refresh_check();
      }
    });
  }
  
  
  