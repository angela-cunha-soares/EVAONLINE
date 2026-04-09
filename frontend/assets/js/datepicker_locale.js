/**
 * DatePicker calendar translation via DOM manipulation.
 * Translates month names and weekday headers when language is Portuguese.
 * Uses MutationObserver to catch calendar popups as they open.
 */
(function () {
    "use strict";

    var MONTHS_EN = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    var MONTHS_PT = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ];

    var WEEKDAYS_EN = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
    var WEEKDAYS_PT = ["Do", "Se", "Te", "Qa", "Qi", "Sx", "Sá"];

    // Current language — read from Dash store
    var currentLang = "en";

    function getLang() {
        try {
            var store = document.getElementById("language-store");
            if (store) {
                var val = store.textContent || store.innerText || "";
                val = val.replace(/["\s]/g, "").trim();
                if (val === "pt" || val === "en") return val;
            }
        } catch (e) { }
        return currentLang;
    }

    function translateCalendars() {
        var lang = getLang();
        currentLang = lang;

        // Translate month captions: ".CalendarMonth_caption strong"
        var captions = document.querySelectorAll(".CalendarMonth_caption strong");
        captions.forEach(function (el) {
            var text = el.textContent.trim();
            if (lang === "pt") {
                for (var i = 0; i < MONTHS_EN.length; i++) {
                    if (text.indexOf(MONTHS_EN[i]) !== -1) {
                        el.textContent = text.replace(MONTHS_EN[i], MONTHS_PT[i]);
                        break;
                    }
                }
            } else {
                for (var i = 0; i < MONTHS_PT.length; i++) {
                    if (text.indexOf(MONTHS_PT[i]) !== -1) {
                        el.textContent = text.replace(MONTHS_PT[i], MONTHS_EN[i]);
                        break;
                    }
                }
            }
        });

        // Translate weekday headers: ".DayPicker_weekHeader_li small"
        var dayHeaders = document.querySelectorAll(".DayPicker_weekHeader_li small");
        dayHeaders.forEach(function (el) {
            var text = el.textContent.trim();
            if (lang === "pt") {
                var idx = WEEKDAYS_EN.indexOf(text);
                if (idx !== -1) el.textContent = WEEKDAYS_PT[idx];
            } else {
                var idx = WEEKDAYS_PT.indexOf(text);
                if (idx !== -1) el.textContent = WEEKDAYS_EN[idx];
            }
        });
    }

    // MutationObserver: watch for calendar popups opening and month changes
    var observer = new MutationObserver(function (mutations) {
        var shouldTranslate = false;
        for (var i = 0; i < mutations.length; i++) {
            var m = mutations[i];
            // Check for added nodes (calendar popup opening)
            if (m.addedNodes && m.addedNodes.length > 0) {
                shouldTranslate = true;
                break;
            }
            // Check for attribute/content changes on calendar elements
            if (m.target && m.target.classList) {
                var cl = m.target.classList;
                if (cl.contains("DayPicker") ||
                    cl.contains("CalendarMonth") ||
                    cl.contains("CalendarMonth_caption") ||
                    cl.contains("SingleDatePicker_picker") ||
                    cl.contains("DayPicker_transitionContainer")) {
                    shouldTranslate = true;
                    break;
                }
            }
        }
        if (shouldTranslate) {
            // Small delay to let react-dates finish rendering
            setTimeout(translateCalendars, 50);
        }
    });

    // Start observing once DOM is ready
    function startObserver() {
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ["class", "style"]
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", startObserver);
    } else {
        startObserver();
    }

    // Also translate when language-store changes (observed via its data attribute)
    // The clientside callback triggers this by writing to the dummy div
    window.dash_clientside = window.dash_clientside || {};
    window.dash_clientside.datepicker_locale = {
        set_locale: function (lang) {
            currentLang = lang || "en";
            setTimeout(translateCalendars, 100);
            return "";
        }
    };
})();
