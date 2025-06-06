// Automatically reload the page if the preferred language doesn't match the expected language
(function auto_switch_language_on_load() {
    const is_guest = frappe.session.user === "Guest";
    const default_lang = "en";
    const user_lang = is_guest ? default_lang : (frappe.boot.lang || default_lang);
    const cookie_lang = frappe.get_cookie("preferred_language") || default_lang;

    // Prevent reload loop
    const switched_lang = sessionStorage.getItem("lang_switched_once");

    // Only update cookie and reload once per session
    if (cookie_lang !== user_lang && !switched_lang) {
        document.cookie = `preferred_language=${user_lang}`;
        document.documentElement.lang = user_lang;
        sessionStorage.setItem("lang_switched_once", "1");

        // Safe redirect instead of reload to avoid CSRF
        window.location.href = window.location.pathname + window.location.search;
    } else {
        document.documentElement.lang = user_lang;
    }
})();

frappe.show_language_picker = function () {
    const is_guest = frappe.session.user === "Guest";
    const default_lang = "en";
    const user_lang = is_guest ? default_lang : (frappe.boot.lang || default_lang);

    // Set preferred language and lang attribute
    document.cookie = `preferred_language=${user_lang}`;
    document.documentElement.lang = user_lang;

    const language_switcher_container = document.getElementById("language-switcher");

    if (!is_guest && window.show_language_picker) {
        // Show the language switcher for logged-in users
        language_switcher_container.classList.remove("hide");

        // Use XHR to fetch language list
        const xhr = new XMLHttpRequest();
        xhr.open("GET", "/api/method/frappe.translate.get_all_languages?with_language_name=true", true);
        xhr.setRequestHeader("Accept", "application/json");
        xhr.onload = function () {
            if (xhr.status === 200) {
                let res = JSON.parse(xhr.responseText);
                let language_list = res.message;

                // Filter to include only zh and en
                language_list = language_list.filter(
                    (language_doc) => ["zh", "en"].includes(language_doc.language_code)
                );

                const language_switcher = $("#language-switcher .form-control");
                language_switcher.empty(); // ✅ Prevent duplicates
                let language_codes = [];

                language_list.forEach((language_doc) => {
                    language_codes.push(language_doc.language_code);
                    language_switcher.append(
                        $("<option></option>")
                            .attr("value", language_doc.language_code)
                            .text(language_doc.language_name)
                    );
                });

                const selected_language = language_codes.includes(user_lang) ? user_lang : default_lang;
                language_switcher.val(selected_language);

                language_switcher.change(() => {
                    const lang = language_switcher.val();
                    fetch("/api/method/cbam.api.set_user_language", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-Frappe-CSRF-Token": frappe.csrf_token
                        },
                        body: JSON.stringify({ lang })
                    }).then(() => {
                        document.cookie = `preferred_language=${lang}`;
                        window.location.href = window.location.pathname + window.location.search;
                    });                    
                });
            }
        };
        xhr.send();
    } else {
        // Hide language switcher for guests
        if (language_switcher_container) {
            language_switcher_container.classList.add("hide");
        }
    }
};

frappe.show_language_picker();