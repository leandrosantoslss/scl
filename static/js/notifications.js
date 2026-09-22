(function () {
    "use strict";
    document.addEventListener("DOMContentLoaded", function () {
        var toggle = document.getElementById("notification-toggle");
        var panel = document.getElementById("notification-panel");
        var list = document.getElementById("notification-list");
        var badge = document.getElementById("notification-badge");
        var readAll = document.getElementById("notification-read-all");
        var deleteAll = document.getElementById("notification-delete-all");
        if (!toggle || !panel || !list) return;
        function html(value) { return String(value == null ? "" : value).replace(/[&<>\"']/g, function (character) { return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]; }); }
        function load() {
            fetch("/api/notificacoes/", { credentials: "same-origin" }).then(function (response) { return response.json(); }).then(function (data) {
                badge.textContent = data.unread || 0; badge.hidden = !(data.unread > 0);
                if (!data.results || !data.results.length) { list.innerHTML = '<div class="text-muted small p-3">Nenhuma notificação.</div>'; return; }
                list.innerHTML = data.results.map(function (item) { var content = '<strong>' + html(item.Titulo) + '</strong><small>' + html(item.Mensagem) + '</small>'; return item.Url ? '<a class="notification-item ' + (!item.Lida ? 'unread' : '') + '" data-notification-id="' + item.CodigoNotificacao + '" href="' + html(item.Url) + '">' + content + '</a>' : '<div class="notification-item ' + (!item.Lida ? 'unread' : '') + '" data-notification-id="' + item.CodigoNotificacao + '">' + content + '</div>'; }).join("");
                list.querySelectorAll("[data-notification-id]").forEach(function (item) { item.addEventListener("click", function () { fetch("/api/notificacoes/" + item.dataset.notificationId + "/ler/", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "" } }); }); });
            }).catch(function () { list.innerHTML = '<div class="text-muted small p-3">Não foi possível carregar as notificações.</div>'; });
        }
        toggle.addEventListener("click", function (event) { event.preventDefault(); panel.hidden = !panel.hidden; if (!panel.hidden) load(); });
        if (readAll) readAll.addEventListener("click", function () { readAll.disabled = true; fetch("/api/notificacoes/ler-todas/", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "" } }).then(function (response) { if (!response.ok) throw new Error(); return response.json(); }).then(load).catch(function () { window.uiMessage("Não foi possível marcar as notificações como lidas.", "Notificações"); }).finally(function () { readAll.disabled = false; }); });
        if (deleteAll) deleteAll.addEventListener("click", async function () { if (!await window.uiConfirm("Excluir todas as notificações? Essa ação não pode ser desfeita.", "Limpar notificações")) return; deleteAll.disabled = true; fetch("/api/notificacoes/limpar-todas/", { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "" } }).then(function (response) { if (!response.ok) throw new Error(); return response.json(); }).then(load).catch(function () { window.uiMessage("Não foi possível limpar as notificações.", "Notificações"); }).finally(function () { deleteAll.disabled = false; }); });
        load();
        window.setInterval(load, 15000);
    });
})();
