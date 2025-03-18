import frappe



def get_context(context):
    context = get_suppliers(context)
    return context
    
@frappe.whitelist()
def get_supplier_partial_html():
    context = {}
    context = get_suppliers(context, re_render=True)
    return frappe.render_template("cbam/templates/supplier_partial.html", context)

def get_suppliers(context, re_render=False):
    from cbam.utils.supplier import get_child_suppliers
   
    supplier_list = get_child_suppliers()
    if re_render:
        context["supplier_list"] = supplier_list
    else:
        context["supplier_list"] = supplier_list
    
    return context