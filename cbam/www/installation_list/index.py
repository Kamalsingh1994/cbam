import frappe
no_cache = 1


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
    
    installations = frappe.get_list("CBAM Installation", fields=["*"])
    for d in installations:
        emissions = [d["emission_data"] for d in frappe.db.get_all("CBAM Emission Data Item", filters={"parent": d.name}, fields=["emission_data"])]
        d.emission_datas = frappe.get_list("CBAM Emission Data", filters= {"name": ["in", emissions]}, fields=['*'])
        #context.installations.append(d)

    context.installations = installations