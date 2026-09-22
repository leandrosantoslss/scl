(function () {
    "use strict";

    function update(input) {
        input.classList.toggle("has-date-value", Boolean(input.value));
    }

    function init() {
        document.querySelectorAll('input[type="date"]').forEach(function (input) {
            update(input);
            input.addEventListener("input", function () { update(input); });
            input.addEventListener("change", function () { update(input); });
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
