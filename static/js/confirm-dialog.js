(function () {
    "use strict";

    window.uiConfirm = function (message, title) {
        return new Promise(function (resolve) {
            var overlay = document.createElement("div");
            overlay.className = "ui-confirm-overlay";
            overlay.innerHTML = '<div class="ui-confirm-dialog" role="dialog" aria-modal="true"><div class="ui-confirm-title"></div><div class="ui-confirm-message"></div><div class="ui-confirm-actions"><button type="button" class="ui-confirm-no">Não</button><button type="button" class="ui-confirm-yes">Sim</button></div></div>';
            overlay.querySelector(".ui-confirm-title").textContent = title || "Confirmação";
            overlay.querySelector(".ui-confirm-message").textContent = message || "Confirma a operação?";
            function finish(value) { overlay.remove(); resolve(value); }
            overlay.querySelector(".ui-confirm-yes").addEventListener("click", function () { finish(true); });
            overlay.querySelector(".ui-confirm-no").addEventListener("click", function () { finish(false); });
            overlay.addEventListener("click", function (event) { if (event.target === overlay) finish(false); });
            document.body.appendChild(overlay);
            overlay.querySelector(".ui-confirm-no").focus();
        });
    };
    window.uiMessage = function (message, title) {
        return new Promise(function (resolve) {
            var overlay = document.createElement("div");
            overlay.className = "ui-confirm-overlay";
            overlay.innerHTML = '<div class="ui-confirm-dialog" role="dialog" aria-modal="true"><div class="ui-confirm-title"></div><div class="ui-confirm-message"></div><div class="ui-confirm-actions"><button type="button" class="ui-confirm-yes">OK</button></div></div>';
            overlay.querySelector(".ui-confirm-title").textContent = title || "Aviso";
            overlay.querySelector(".ui-confirm-message").textContent = message || "Operação concluída.";
            function finish() { overlay.remove(); resolve(); }
            overlay.querySelector(".ui-confirm-yes").addEventListener("click", finish);
            overlay.addEventListener("click", function (event) { if (event.target === overlay) finish(); });
            document.body.appendChild(overlay);
            overlay.querySelector(".ui-confirm-yes").focus();
        });
    };
}());
