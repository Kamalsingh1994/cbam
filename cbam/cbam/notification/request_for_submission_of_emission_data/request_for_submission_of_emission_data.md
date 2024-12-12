<p>Dear {{doc.main_contact_employee_last_name}},</p>

<p>{{frappe.db.get_value("User", frappe.session.user, 'title')}} has requested you to submit data on the behalf of {{doc.supplier_name}}.</p>

<p>please <a href= "frappe.utils.get_url()/login#login-with-email-link">login</a> to CBAM-Platform and submit the emission data.</p>

<p>Thanks,
CBAM</p>
