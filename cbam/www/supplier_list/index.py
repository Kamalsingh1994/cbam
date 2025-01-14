import frappe



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
    # else:
    #     context.goods_list = []
    context = get_suppliers(context)
    return
    context.supplier_list = frappe.db.get_all("Supplier")
    
@frappe.whitelist()
def get_supplier_partial_html():
    context = {}
    context = get_suppliers(context, re_render=True)
    return frappe.render_template("cbam/templates/supplier_partial.html", context)

def get_suppliers(context, re_render=False):
    filters = {"commercial_contact_user": frappe.session.user}
    if "CBAM Representative" in frappe.get_roles():
        filters = {"cbam_representative_user": frappe.session.user}
    supplier_list = frappe.db.get_all("Operating Company", {"parent_operating_company": frappe.db.get_value("Operating Company", filters, "name")})
    if re_render:
        context["supplier_list"] = supplier_list
    else:
        context.supplier_list = supplier_list
    
    return context