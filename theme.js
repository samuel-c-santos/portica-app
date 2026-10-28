/* Pórtica App — alternância de tema claro/escuro (sem CDN, JS mínimo).
 *
 * O design system Aipim já traz claro/escuro: <html data-theme="dark"> força o
 * escuro, <html data-theme="light"> força o claro e, sem atributo, segue o
 * sistema. Aqui resolvemos o tema no carregamento (sem piscar), ligamos o
 * botão de alternância e trocamos as imagens que têm versão clara/escura
 * (atributo data-theme-img-light / data-theme-img-dark).
 */
(function () {
  "use strict";

  var KEY = "portica-theme";
  var root = document.documentElement;

  function resolve() {
    try {
      var s = window.localStorage.getItem(KEY);
      if (s === "light" || s === "dark") return s;
    } catch (e) { /* storage indisponível */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function swapImages(theme) {
    var imgs = document.querySelectorAll("[data-theme-img]");
    for (var i = 0; i < imgs.length; i++) {
      var src = theme === "dark"
        ? imgs[i].getAttribute("data-theme-img-dark")
        : imgs[i].getAttribute("data-theme-img-light");
      if (src) imgs[i].setAttribute("src", src);
    }
  }

  function apply(theme, persist) {
    root.setAttribute("data-theme", theme);
    if (persist) {
      try { window.localStorage.setItem(KEY, theme); } catch (e) { /* ok */ }
    }
    swapImages(theme);
  }

  // 1) Tema inicial, antes do primeiro paint (evita "flash").
  apply(resolve(), false);

  // 2) Depois que o DOM existe: troca as imagens e liga o botão.
  function boot() {
    var theme = root.getAttribute("data-theme") || resolve();
    swapImages(theme);

    var btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        apply(next, true);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
