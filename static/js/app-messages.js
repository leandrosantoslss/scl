(function () {
    "use strict";

    function showAppMessages() {
        if (document.querySelector("[data-distrato-form]")) return;
        var messages = Array.from(document.querySelectorAll("[data-app-message]"));

        function showNext(index) {
            if (index >= messages.length) return;
            var message = messages[index].textContent.trim();
            if (!message) { showNext(index + 1); return; }
            window.uiMessage(message, messages[index].dataset.uiMessageTitle || "Aviso").then(function () {
                showNext(index + 1);
            });
        }

        showNext(0);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", showAppMessages);
    else showAppMessages();
}());
