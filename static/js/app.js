(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        var miniButton = document.getElementById("menu-mini-button");
        var mobileButton = document.getElementById("mobile-collapse");
        var navigation = document.querySelector(".nxl-navigation");
        var profileToggle = document.getElementById("profile-dropdown-toggle");
        var profileWrapper = document.getElementById("profile-dropdown-wrapper");
        var themeToggle = document.getElementById("theme-toggle");
        var themeIcon = document.getElementById("theme-toggle-icon");
        var fullscreenToggle = document.getElementById("fullscreen-toggle");
        var fullscreenMaximizeIcon = document.getElementById("fullscreen-maximize-icon");
        var fullscreenMinimizeIcon = document.getElementById("fullscreen-minimize-icon");

        function applyTheme(theme) {
            var dark = theme === "dark";
            document.documentElement.classList.toggle("app-skin-dark", dark);
            document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
            if (themeIcon) themeIcon.className = dark ? "feather-sun" : "feather-moon";
            if (themeToggle) themeToggle.setAttribute("aria-label", dark ? "Usar tema claro" : "Usar tema escuro");
        }

        var savedTheme = "light";
        try { savedTheme = window.localStorage.getItem("lotesis-theme") === "dark" ? "dark" : "light"; } catch (error) {}
        applyTheme(savedTheme);

        if (themeToggle) {
            themeToggle.addEventListener("click", function (event) {
                event.preventDefault();
                var next = document.documentElement.classList.contains("app-skin-dark") ? "light" : "dark";
                applyTheme(next);
                try { window.localStorage.setItem("lotesis-theme", next); } catch (error) {}
            });
        }

        function updateFullscreenControl() {
            var active = Boolean(document.fullscreenElement);
            if (fullscreenMaximizeIcon) fullscreenMaximizeIcon.style.display = active ? "none" : "inline-block";
            if (fullscreenMinimizeIcon) fullscreenMinimizeIcon.style.display = active ? "inline-block" : "none";
            if (fullscreenToggle) fullscreenToggle.setAttribute("aria-label", active ? "Sair da tela cheia" : "Tela cheia");
        }
        if (fullscreenToggle) fullscreenToggle.addEventListener("click", function (event) {
            event.preventDefault();
            if (document.fullscreenElement) document.exitFullscreen();
            else document.documentElement.requestFullscreen();
        });
        document.addEventListener("fullscreenchange", updateFullscreenControl);
        updateFullscreenControl();

        if (miniButton) {
            miniButton.addEventListener("click", function (event) {
                event.preventDefault();
                document.documentElement.classList.toggle("minimenu");
            });
        }

        if (mobileButton && navigation) {
            mobileButton.addEventListener("click", function (event) {
                event.preventDefault();
                navigation.classList.toggle("mob-navigation-active");
            });
        }

        if (profileToggle && profileWrapper) {
            profileToggle.addEventListener("click", function (event) {
                event.preventDefault();
                profileWrapper.classList.toggle("is-open");
                profileToggle.setAttribute("aria-expanded", profileWrapper.classList.contains("is-open") ? "true" : "false");
            });
            document.addEventListener("click", function (event) {
                if (!profileWrapper.contains(event.target)) {
                    profileWrapper.classList.remove("is-open");
                    profileToggle.setAttribute("aria-expanded", "false");
                }
            });
        }
    });
})();
