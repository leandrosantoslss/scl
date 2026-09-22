(function () {
    function setCompanyName(name) {
        var target = document.getElementById("company-name");
        var value = String(name || "").trim();
        if (!target || !value) return;
        target.textContent = value;
        try {
            window.localStorage.setItem("companyName", value);
        } catch (error) {
            // Local storage is optional; the server-rendered name remains available.
        }
    }

    function init() {
        var username = document.getElementById("id_username");
        var password = document.getElementById("id_password");
        var form = document.querySelector(".login-form");
        var submit = document.getElementById("login-submit");
        var submitLabel = document.getElementById("login-submit-label");
        var spinner = document.getElementById("btn-spinner");
        var progress = document.getElementById("login-progress");
        var company = document.getElementById("company-name");

        if (username) {
            username.focus();
            username.select();
            username.addEventListener("keydown", function (event) {
                if (event.key === "Enter" && password) {
                    event.preventDefault();
                    password.focus();
                    password.select();
                }
            });
        }

        try {
            var storedCompany = window.localStorage.getItem("companyName");
            if (storedCompany) setCompanyName(storedCompany);
        } catch (error) {
            // Local storage is optional.
        }

        fetch("/api/empresas/licenca", { headers: { Accept: "application/json" } })
            .then(function (response) {
                if (!response.ok) throw new Error("license lookup failed");
                return response.json();
            })
            .then(function (data) {
                setCompanyName(data.nome || data.fantasia);
            })
            .catch(function () {
                // The default/server-rendered company name is intentionally retained.
            });

        if (form) {
            form.addEventListener("submit", function () {
                if (!username || !password || !username.value || !password.value) return;
                if (submit) submit.disabled = true;
                if (progress) progress.hidden = false;
                if (spinner) spinner.hidden = false;
                if (submitLabel) submitLabel.textContent = "Entrando...";
            });
        }

        if (company && !company.textContent.trim()) {
            company.textContent = company.dataset.defaultCompany || "RESIDENCIAL JARDIM IRENE";
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
