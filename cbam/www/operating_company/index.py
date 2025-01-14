import frappe
no_cache = 1
from cbam.utils import get_supplier

def get_context(context):
    # context.user = frappe.session.user
    # context.employee_list = frappe.db.get_all('Supplier Employee', filters={'email': context.user}, fields=['name'], pluck="name")
    # if context.employee_list:
    #     context.employee = context.employee_list[0]
    #     context.goods_list = frappe.get_all('Good', 
    #         filters={'employee': context.employee}, 
    #         or_filters=[["status", "like", "Raw Data"], ["status", "like", "Sent for completing"], ["status", "like", "Done"]], 
    #         fields=[
    #             "*"
    #         ]
    #     )
    
    # context.emission_datas = []
    context = get_operating_company(context)
    
@frappe.whitelist()
def get_operating_company_partial_html():
    context = {}
    context = get_operating_company(context, re_render=True)
    return frappe.render_template("cbam/templates/operating_company_partial.html", context)

def get_operating_company(context, re_render=False):
    supplier = get_supplier()
    if supplier:
        doc = frappe.get_doc("Operating Company", supplier)
        if re_render:
            context["doc"] = doc
        else:
            context.doc = doc
        return context
    else:
        return False
    