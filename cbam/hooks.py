app_name = "cbam"
app_title = "CBAM"
app_publisher = "phamos GmbH"
app_description = "Handling The EU\'s Carbon Border Adjustment Mechanism (CBABAM))"
app_email = "wolfram.schmidt@phamos.eu"
app_license = "mit"

after_install = "cbam.utils.after_install.after_install"
#update boot context
boot_session = "cbam.boot.update_boot_context"
extend_bootinfo = "cbam.boot.update_website_context"
website_context = {
    "logo": "assets/cbam/images/gallehr_partner_logo.png",
    "splash_image": "assets/cbam/images/gallehr_partner_logo.png"
}
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cbam",
# 		"logo": "assets/cbam/images/gallehr_partner_logo.png"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/cbam/css/cbam.css"
app_include_js = [
    "cbam.bundle.js",
    "cbam-utils.bundle.js"
]


# include js, css files in header of web template
#web_include_css = "/assets/cbam/css/cbam.css"
web_include_js = [
    "controls.bundle.js",
    "cbam.bundle.js",
    "cbam-utils.bundle.js"
]

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cbam/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}

# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

after_migrate = [
    "cbam.utils.translation.remove_duplicate_translations",
    "cbam.utils.utils.update_workspace_for_helpdesk",
    "cbam.utils.utils.add_helpdesk_navbar_item",
    "cbam.utils.utils.remove_user_access_for_desk_user",
    "cbam.utils.utils.update_workspace_roles",
    "cbam.utils.after_install.create_dynamic_web_templates_if_not_exists",
]
# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cbam/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Commercial Contact": "home"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cbam.utils.jinja_methods",
# 	"filters": "cbam.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cbam.install.before_install"
# after_install = "cbam.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "cbam.uninstall.before_uninstall"
# after_uninstall = "cbam.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cbam.utils.before_app_install"
# after_app_install = "cbam.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cbam.utils.before_app_uninstall"
# after_app_uninstall = "cbam.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cbam.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"Workspace": {
# 		"on_update": "cbam.doc_events_workspace_role.add_reporting_declarant_role",
# 		# "on_cancel": "method",
# 		# "on_trash": "method"
# 	}
# }

doc_events = {
    "Operating Company": {
        "on_update": "cbam.cbam.doctype.operating_company.operating_company.update_goods_on_operating_company_change"
    },
    "User": {
        "before_save": "cbam.override.user.update_operating_company_contact"
    },
    "File": {
        "on_trash": "cbam.utils.utils.prevent_declarant_file_delete"
    },
    "CBAM Emission Data": {
        "on_update": "cbam.cbam.doctype.good.good.update_good_sidebar_on_emission_data_update"
    }
}


# Scheduled Tasks
# ---------------

scheduler_events = {
    "cron": {
        "0 21 * * *": [
            "cbam.utils.notification.generate_alerts"
        ]
    },
    "daily":[
        "cbam.utils.ets_import.scheduled_import.scheduled_ets_import"
    ],
    "daily": [
        "cbam.cbam.page.various_cost_comparisons.missing_data_email.send_missing_data_summary"
    ]
}

# Testing
# -------

# before_tests = "cbam.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.core.doctype.user.user.update_password": "cbam.override.user.update_password"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cbam.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cbam.utils.before_request"]
# after_request = ["cbam.utils.after_request"]

# Job Events
# ----------
# before_job = ["cbam.utils.before_job"]
# after_job = ["cbam.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cbam.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [

    {"dt": "Role", "filters": [
        [
            "name", "in", [
                "Declarant",
                "Commercial Contact",
                "CBAM Representative"
            ]
        ]
    ]
    },
    {"dt": "Module Profile", "filters": [
        [
            "name", "in", [
                "Declarant"
            ]
        ]
    ]}
    # {"dt": "Custom DocPerm", "filters": [
    #     [
    #         "role", "in", [
    #             "Supplier",
    #             "Reporting Declarant",
    #         ]
    #     ]
    # ]},
    #  {"dt": "Notification", "filters": [
    #     [
    #         "name", "in", [
    #             "Tier n+1 Unregistered Supplier Template",
    #             "Tier n+1 Registered Supplier Template",
    #             "Tier 1 Unregistered Employee Template",
    #             "Tier 1 Registered Employee Template",
    #             "Supplier Good Rejection Notification Template"
    #         ]
    #     ]
    # ]
    # },
]

permission_query_conditions = {
    "User": "cbam.utils.utils.user_permission_query"
}
