import frappe
from cbam.utils import get_roles, require_website_user
from cbam.utils.supplier import get_supplier
no_cache = 1


def get_context(context):
    require_website_user()
    context = get_user_roles(context)
    context = get_goods_list(context)
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
    # else:
    #     context.goods_list = []
    
@frappe.whitelist()
def get_goods_partial_html():
    context = {}
    context = get_user_roles(context, re_render=True)
    context = get_goods_list(context, True)
    return frappe.render_template("cbam/templates/goods_partial.html", context)

def get_user_roles(context, re_render=False):
    roles = get_roles(frappe.session.user)
    if re_render:
        context["roles"] =  roles
    else:
        context.roles = roles
        
    return context

def get_goods_list(context, re_render=False):
    # Build filters for goods list
    # Filter by operating company and exclude only Draft status
    # Include Rejected status so parent companies can see rejected goods reassigned to them
    operating_company = get_supplier()
    filters = {"status": ["!=", "Draft"]}
    if operating_company:
        filters["operating_company"] = operating_company
    goods_list = frappe.db.get_list("Good", filters=filters)
    
    if re_render:
        context["goods_list"] = goods_list
    else:
        context.goods_list = goods_list
    return context

    