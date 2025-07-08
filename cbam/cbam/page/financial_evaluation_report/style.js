frappe.provide('cbam')

cbam.inject_custom_styles = function inject_custom_styles(body) {
    $(body).append(`
        <style>
            .stat-card.frappe-card {
                min-width: 230px;
                max-width: 260px;
            }
            .filter-clear-btn {
                min-width: 70px;
                margin-left: 8px;
            }
            @media (max-width: 991px) {
                .stat-card.frappe-card {
                    min-width: 180px;
                    max-width: 100%;
                }
            }
            .dt-cell__content--col-0 {
                width: unset !important;
            }
            /* Checkbox column alignment fix */
            .dt-cell--col-0, .dt-header__cell--col-0 {
                min-width: 40px !important;
                max-width: 40px !important;
                width: 40px !important;
                text-align: center;
            }
            /* Table toggle section styles */
            #table-toggle-section {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border: 1px solid #dee2e6;
            }
            /* Compact Toggle Switch Styles */
            .switch-compact {
                position: relative;
                display: inline-block;
                width: 40px;
                height: 20px;
            }
            
            .switch-compact input {
                opacity: 0;
                width: 0;
                height: 0;
            }
            
            .slider-compact {
                position: absolute;
                cursor: pointer;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background-color: #ccc;
                -webkit-transition: .3s;
                transition: .3s;
            }
            
            .slider-compact:before {
                position: absolute;
                content: "";
                height: 14px;
                width: 14px;
                left: 3px;
                bottom: 3px;
                background-color: white;
                -webkit-transition: .3s;
                transition: .3s;
            }
            
            input:checked + .slider-compact {
                background-color: #2196F3;
            }
            
            input:focus + .slider-compact {
                box-shadow: 0 0 1px #2196F3;
            }
            
            input:checked + .slider-compact:before {
                -webkit-transform: translateX(20px);
                -ms-transform: translateX(20px);
                transform: translateX(20px);
            }
            
            .slider-compact.round {
                border-radius: 20px;
            }
            
            .slider-compact.round:before {
                border-radius: 50%;
            }
            
            #table-toggle-section {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                border: 1px solid #dee2e6;
            }
        </style>
    `);
}