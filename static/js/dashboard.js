(function () {
    "use strict";

    var COLORS = ["#17c666", "#ffa21d", "#7655c7", "#3454d1", "#dc2626"];

    function readJson(id, fallback) {
        var node = document.getElementById(id);
        if (!node) return fallback;
        try {
            return JSON.parse(node.textContent);
        } catch (error) {
            return fallback;
        }
    }

    function renderStatusChart() {
        var container = document.getElementById("status-chart");
        var values = readJson("status-values", []);
        if (!container) return;
        var total = values.reduce(function (sum, value) { return sum + Number(value || 0); }, 0);
        if (!total) {
            container.innerHTML = '<div class="chart-empty">Nenhum lote cadastrado.</div>';
            return;
        }

        var namespace = "http://www.w3.org/2000/svg";
        var svg = document.createElementNS(namespace, "svg");
        svg.setAttribute("viewBox", "0 0 180 180");
        svg.setAttribute("width", "180");
        svg.setAttribute("height", "180");
        var center = 90;
        var radius = 70;
        var start = -Math.PI / 2;

        values.forEach(function (rawValue, index) {
            var value = Number(rawValue || 0);
            if (!value) return;
            var angle = value / total * Math.PI * 2;
            var end = start + angle;
            var x1 = center + radius * Math.cos(start);
            var y1 = center + radius * Math.sin(start);
            var x2 = center + radius * Math.cos(end);
            var y2 = center + radius * Math.sin(end);
            var path = document.createElementNS(namespace, "path");
            path.setAttribute("d", "M " + center + " " + center + " L " + x1 + " " + y1 + " A " + radius + " " + radius + " 0 " + (angle > Math.PI ? 1 : 0) + " 1 " + x2 + " " + y2 + " Z");
            path.setAttribute("fill", COLORS[index % COLORS.length]);
            path.setAttribute("opacity", "0.9");
            svg.appendChild(path);
            start = end;
        });

        var outline = document.createElementNS(namespace, "circle");
        outline.setAttribute("cx", center);
        outline.setAttribute("cy", center);
        outline.setAttribute("r", radius);
        outline.setAttribute("fill", "none");
        outline.setAttribute("stroke", "#e5e7eb");
        outline.setAttribute("stroke-width", "1");
        svg.appendChild(outline);
        container.appendChild(svg);
    }

    function monthLabel(value) {
        var parts = String(value || "").split("-");
        return parts.length === 2 ? parts[1] + "/" + parts[0].slice(-2) : value;
    }

    function renderMonthlyChart() {
        var container = document.getElementById("monthly-chart");
        var months = readJson("contract-months", []);
        var values = readJson("contract-values", []);
        if (!container) return;
        var max = Math.max.apply(Math, [1].concat(values.map(function (value) { return Number(value || 0); })));

        months.forEach(function (month, index) {
            var value = Number(values[index] || 0);
            var column = document.createElement("div");
            column.className = "month-column";
            column.title = monthLabel(month) + ": " + value + " contrato(s)";

            var number = document.createElement("span");
            number.className = "month-value";
            number.textContent = value;

            var bar = document.createElement("span");
            bar.className = "month-bar";
            bar.style.height = Math.max(value ? (value / max) * 145 : 2, 2) + "px";

            var label = document.createElement("span");
            label.className = "month-label";
            label.textContent = monthLabel(month);

            column.appendChild(number);
            column.appendChild(bar);
            column.appendChild(label);
            container.appendChild(column);
        });

        if (!months.length) {
            container.innerHTML = '<div class="chart-empty">Nenhum contrato no período.</div>';
        }
    }

    function init() {
        renderStatusChart();
        renderMonthlyChart();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
