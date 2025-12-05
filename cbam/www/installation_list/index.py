import frappe
from cbam.utils import require_website_user
no_cache = 1


def get_context(context):
    require_website_user()
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
    
    context = get_installations(context)
    
@frappe.whitelist()
def get_installation_partial_html():
    context = {}
    context = get_installations(context, True)

    return frappe.render_template("cbam/templates/installation_partial.html", context)

def get_installations(context, re_render=False):
    from cbam.utils.supplier import get_supplier
    installations = frappe.get_all("CBAM Installation", filters = {"operating_company": get_supplier()}, fields=["*"])
    for d in installations:
        emissions = [d["emission_data"] for d in frappe.db.get_all("CBAM Emission Data Item", filters={"parent": d.name}, fields=["emission_data"])]
        d.emission_datas = frappe.get_all("CBAM Emission Data", filters= {"name": ["in", emissions]}, fields=['*'])
        #context.installations.append(d)
    if re_render:
        context["installations"] = installations
    else:
        context.installations = installations
    return context
    