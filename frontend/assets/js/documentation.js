/*
 * Documentation page enhancements:
 *  - Scroll-spy (highlight active section in the sidebar)
 *  - Back-to-top floating button
 *  - FAQ live search filter
 *  - Clickable anchor links on section titles
 * Works with Dash SPA navigation via a MutationObserver re-init.
 */
(function () {
  "use strict";

  function initScrollSpy() {
    var nav = document.querySelector(".doc-sidebar-nav");
    if (!nav) return;
    var links = Array.prototype.slice.call(
      nav.querySelectorAll(".doc-nav-link")
    );
    if (!links.length) return;

    var byId = {};
    var targets = [];
    links.forEach(function (l) {
      var id = (l.getAttribute("href") || "").replace("#", "");
      var el = id && document.getElementById(id);
      if (el) {
        byId[id] = l;
        targets.push(el);
      }
    });
    if (!targets.length) return;

    if (window.__docSpyObs) {
      window.__docSpyObs.disconnect();
    }
    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            links.forEach(function (l) {
              l.classList.remove("active");
            });
            var l = byId[e.target.id];
            if (l) l.classList.add("active");
          }
        });
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );
    targets.forEach(function (t) {
      obs.observe(t);
    });
    window.__docSpyObs = obs;
  }

  function initAnchors() {
    var titles = document.querySelectorAll(".doc-section-title[id]");
    titles.forEach(function (h) {
      if (h.querySelector(".doc-anchor")) return;
      var a = document.createElement("a");
      a.className = "doc-anchor";
      a.href = "#" + h.id;
      a.setAttribute("aria-label", "Link to this section");
      a.textContent = "#";
      h.appendChild(a);
    });
  }

  function initBackToTop() {
    var btn = document.getElementById("doc-back-to-top");
    if (!btn || btn.dataset.init) return;
    btn.dataset.init = "1";
    function onScroll() {
      if (window.scrollY > 400) btn.classList.add("show");
      else btn.classList.remove("show");
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    onScroll();
  }

  function initFaqSearch() {
    var input = document.getElementById("faq-search");
    if (!input || input.dataset.init) return;
    input.dataset.init = "1";
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      var faq = document.getElementById("faq-accordion");
      if (!faq) return;
      var items = faq.querySelectorAll(".accordion-item");
      var any = false;
      items.forEach(function (it) {
        var txt = (it.textContent || "").toLowerCase();
        var match = !q || txt.indexOf(q) !== -1;
        it.style.display = match ? "" : "none";
        if (match) any = true;
      });
      var empty = document.getElementById("faq-empty");
      if (empty) empty.style.display = any ? "none" : "";
    });
  }

  function initDocs() {
    if (!document.getElementById("doc-content")) return;
    initScrollSpy();
    initAnchors();
    initBackToTop();
    initFaqSearch();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDocs);
  } else {
    initDocs();
  }

  // Re-initialize when Dash swaps the page content (SPA navigation).
  var mo = new MutationObserver(function () {
    if (document.getElementById("doc-content")) {
      clearTimeout(window.__docInitT);
      window.__docInitT = setTimeout(initDocs, 150);
    }
  });
  mo.observe(document.body, { childList: true, subtree: true });
})();
