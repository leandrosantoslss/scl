(function () {
    "use strict";

    var CNPJ_API = "https://api.opencnpj.org/";
    var CEP_API = "https://viacep.com.br/ws/";

    function setValue(id, value, force) {
        var field = document.getElementById(id);
        if (field && (force || !field.value)) field.value = value || "";
    }

    function setHint(id, text) {
        var hint = document.getElementById(id);
        if (hint) hint.textContent = text || "";
    }

    function compactDocument(value) {
        return String(value || "").replace(/\D/g, "");
    }

    function maskCnpj(digits) {
        var value = String(digits || "").replace(/\D/g, "").slice(0, 14);
        if (value.length <= 2) return value;
        if (value.length <= 5) return value.slice(0, 2) + "." + value.slice(2);
        if (value.length <= 8) return value.slice(0, 2) + "." + value.slice(2, 5) + "." + value.slice(5);
        if (value.length <= 11) return value.slice(0, 2) + "." + value.slice(2, 5) + "." + value.slice(5, 8) + "/" + value.slice(8);
        return value.slice(0, 2) + "." + value.slice(2, 5) + "." + value.slice(5, 8) + "/" + value.slice(8, 12) + "-" + value.slice(12);
    }

    function maskCep(value) {
        var digits = String(value || "").replace(/\D/g, "").slice(0, 8);
        if (digits.length <= 5) return digits;
        return digits.slice(0, 5) + "-" + digits.slice(5);
    }

    function loadCnpj() {
        var field = document.getElementById("id_cnpjcpf");
        var digits = compactDocument(field ? field.value : "");
        if (digits.length !== 14) {
            setHint("cnpj-lookup-hint", "CNPJ deve ter 14 dígitos.");
            return;
        }
        setHint("cnpj-lookup-hint", "Consultando CNPJ...");
        fetch(CNPJ_API + digits).then(function (response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            return response.json();
        }).then(function (data) {
            if (!data || data.erro) throw new Error("não encontrado");
            setValue("id_nome", data.razao_social || data.nome_fantasia, true);
            if (data.email) setValue("id_email", (data.usuarios || "").trim() || "", true);
            if (data.logradouro) setValue("id_endereco", (data.logradouro || "").trim(), true);
            setValue("id_endnumero", data.numero, true);
            setValue("id_endcomplemento", data.complemento, true);
            setValue("id_endbairro", data.bairro, true);
            setValue("id_endUF", data.estado && data.estado.tld ? data.estado.tld.toUpperCase() : "", true);
            setValue("id_endcidade", data.cidade && data.cidade.name ? data.cidade.name : "", true);
            setValue("id_cep", maskCep(data.cep), true);
            setHint("cnpj-lookup-hint", "CNPJ preenchido com sucesso.");
        }).catch(function () {
            setHint("cnpj-lookup-hint", "Não foi possível recuperar o CNPJ, verifique e tente novamente.");
        });
    }

    function loadCep() {
        var field = document.getElementById("id_cep");
        var digits = compactDocument(field ? field.value : "");
        if (digits.length !== 8) return;
        fetch(CEP_API + digits + "/json/").then(function (response) {
            return response.json();
        }).then(function (data) {
            if (!data || data.erro) return;
            setValue("id_endereco", data.logradouro, true);
            setValue("id_endbairro", data.bairro, true);
            setValue("id_endUF", data.uf, true);
            setValue("id_endcidade", data.localidade, true);
        }).catch(function () {});
    }

    function init() {
        var cnpj = document.getElementById("id_cnpjcpf");
        var lookupBtn = document.getElementById("lookup-cnpj");
        var zip = document.getElementById("id_cep");
        var zipBtn = document.getElementById("lookup-zip");

        if (cnpj) {
            cnpj.addEventListener("input", function () {
                cnpj.value = maskCnpj(cnpj.value);
            });
            cnpj.addEventListener("blur", function () {
                if (compactDocument(cnpj.value).length === 14) loadCnpj();
                else setHint("cnpj-lookup-hint", "");
            });
            cnpj.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); loadCnpj(); }
            });
        }
        if (lookupBtn) lookupBtn.addEventListener("click", loadCnpj);

        if (zip) {
            zip.addEventListener("input", function () {
                zip.value = maskCep(zip.value);
            });
            zip.addEventListener("blur", loadCep);
            zip.addEventListener("keydown", function (event) {
                if (event.key === "Enter") { event.preventDefault(); loadCep(); }
            });
        }
        if (zipBtn) zipBtn.addEventListener("click", loadCep);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
