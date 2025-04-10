frappe.show_language_picker = function () {
if (frappe.session.user && window.show_language_picker) {
    frappe
        .call("frappe.translate.get_all_languages", {
            with_language_name: true,
        })
        .then((res) => {
            let language_list = res.message;
            // Filter the language list to include only Chinese (zh) and English (en)
            language_list = language_list.filter((language_doc) => 
                language_doc.language_code === "zh" || language_doc.language_code === "en"
            );
            let language = frappe.get_cookie("preferred_language");
            let language_codes = [];
            let language_switcher = $("#language-switcher .form-control");
            language_list.forEach((language_doc) => {
                language_codes.push(language_doc.language_code);
                language_switcher.append(
                    $("<option></option>")
                        .attr("value", language_doc.language_code)
                        .text(language_doc.language_name)
                );
            });
            $("#language-switcher").removeClass("hide");
            language =
                language ||
                (language_codes.includes(navigator.language) ? navigator.language : "en");
            language_switcher.val(language);
            document.documentElement.lang = language;
            language_switcher.change(() => {
                frappe.call({
                    method: "cbam.api.set_user_language",
                    args: {
                        lang: $('#language-switcher select').val()
                    }
                });
                const lang = language_switcher.val();
                document.cookie = `preferred_language=${lang}`;
                setInterval(() => {
                    window.location.reload();
                }, 1000);
            });
        });
    }
}
frappe.show_language_picker();

