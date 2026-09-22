(function () {
    "use strict";

    // Ações de Enter: focus → próximo field interativo, último input submete o form.
    // Padrão aplicável a todos os forms do portal (login, cadastro, filtros, etc).
    function campoAtivo(elemento) {
        if (!elemento) return false;
        var tag = (elemento.tagName || "").toLowerCase();
        if (tag !== "input" && tag !== "select" && tag !== "textarea") return false;
        var tipo = (elemento.getAttribute("type") || "").toLowerCase();
        if (elemento.disabled || elemento.readOnly) return false;
        if (tipo === "hidden") return false;
        if (tag === "select") return !elemento.multiple;
        return true;
    }

    function proximoInteragivel(elemento) {
        var todos = Array.from(
            document.querySelectorAll(
                "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']), select, textarea"
            )
        );
        var visiveis = todos.filter(function (campo) {
            return !campo.disabled && !campo.readOnly && campo.offsetParent !== null;
        });
        var indice = visiveis.indexOf(elemento);
        if (indice < 0 || indice === visiveis.length - 1) return null;
        return visiveis[indice + 1];
    }

    function init() {
        document.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            var origem = event.target;
            if (!origem || origem === document.body) return;

            var tag = (origem.tagName || "").toLowerCase();
            if (tag === "textarea") return;
            if ((origem.getAttribute("type") || "").toLowerCase() === "search") return;

            var form = origem.form || (origem.closest ? origem.closest("form") : null);
            if (!form) return;

            // Se a origem já é o botão de submit, deixa o comportamento native.
            var tipo = (origem.getAttribute("type") || "").toLowerCase();
            if (tipo === "submit" || tipo === "reset" || tipo === "button") return;

            event.preventDefault();

            var proximo = proximoInteragivel(origem);
            if (proximo) {
                proximo.focus();
                if (proximo.select) proximo.select();
                return;
            }

            // Último campo do form: submete.
            if (typeof form.requestSubmit === "function") {
                form.requestSubmit();
            } else {
                form.submit();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
