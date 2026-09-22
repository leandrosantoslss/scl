(function () {
    "use strict";
    var timeout = Number(window.LOTISIS_SESSION_TIMEOUT || 1800) * 1000;
    var timer;
    function expire() {
        var next = window.location.pathname + window.location.search;
        window.uiMessage("Sua sessão foi encerrada por inatividade. Faça login novamente para continuar.", "Sessão expirada").then(function () {
            window.location.href = "/login/?next=" + encodeURIComponent(next);
        });
    }
    function reset() {
        window.clearTimeout(timer);
        timer = window.setTimeout(expire, timeout);
    }
    ["click", "keydown", "mousemove", "scroll", "touchstart"].forEach(function (eventName) {
        document.addEventListener(eventName, reset, { passive: true });
    });
    reset();
})();
