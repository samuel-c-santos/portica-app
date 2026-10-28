/* Aipim design system · https://github.com/talis-galhardi/aipim · MIT License · Copyright (c) 2026 Talis Galhardi */
/* Optional behavior for the components that need a little script. The CSS works without it.
   - [data-aipim-dismiss] on a button removes the closest alert, toast or tag and moves focus to the next focusable element.
     It fires a cancelable "aipim:dismiss" event first, so your code can react or stop it.
   - .aipim-tabs[role=tablist]: click, arrow keys, Home and End, aria-selected, roving tabindex and panel visibility.
     When a tab is chosen after the top of the screen went below the top edge of the list, the page scrolls so the
     list is at the top of the screen, always at the same height (a sticky list is read where it sits in the page), so
     the new panel starts at its top instead of keeping the scroll of the tab before.
   - Modal: button[command][commandfor] for browsers without invoker commands (show-modal and close).
   - Brazilian field: input[data-aipim-format] (cpf, cnpj, cep, phone, date, money) gets its mask while you type and is
     checked when you leave it. Aipim.br has the same format and check as plain functions, for frameworks and servers.
   - Combobox: input[role=combobox][aria-controls] filters its listbox while you type, with arrows, Enter and Escape.
   - Date picker: .aipim-datepicker__button next to a date field opens a calendar (ARIA date picker dialog).
   - Aipim.init(container): sets up tabs, comboboxes and date pickers and formats the Brazilian fields in content added after the page loaded. */
(function () {
  'use strict';

  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  function focusAfter(el) {
    var all = Array.prototype.filter.call(document.querySelectorAll(FOCUSABLE), function (n) {
      return !el.contains(n) && n.getClientRects().length > 0;
    });
    var next = all.filter(function (n) {
      return el.compareDocumentPosition(n) & Node.DOCUMENT_POSITION_FOLLOWING;
    })[0] || all[all.length - 1];
    if (next) next.focus();
  }

  function dismiss(button) {
    var item = button.closest('.aipim-toast, .aipim-alert, .aipim-tag');
    if (!item) return;
    if (!item.dispatchEvent(new CustomEvent('aipim:dismiss', { bubbles: true, cancelable: true }))) return;
    focusAfter(item);
    if (item.classList.contains('aipim-toast')) {
      // The exit animation is 100ms, or 0ms with reduced motion. The timeout is a safety net.
      item.setAttribute('data-state', 'closing');
      var remove = function () { item.remove(); };
      item.addEventListener('animationend', remove, { once: true });
      setTimeout(remove, 400);
    } else {
      item.remove();
    }
  }

  // The element that makes `el` stick to the top of the screen: `el` itself or one of its ancestors with position:sticky.
  function stickyOf(el) {
    for (var n = el; n && n !== document.body; n = n.parentElement) {
      if (getComputedStyle(n).position === 'sticky') return n;
    }
    return null;
  }

  // Where the top edge of `el` is on the screen, in the flow of the page. A stuck element reports the place it is stuck
  // at, not the place it holds in the page, and CSS has no way to ask for that one. So it is read with the element as
  // `static` for the instant of the measure (no frame is painted in between), then it is put back. The alternatives
  // were worse: a probe element inside the layout adds a flex or grid item (and its gap), and the sibling before the
  // element does not say what margins or gaps lie between them.
  function flowTop(el) {
    var was = el.style.position;
    el.style.position = 'static';
    var top = el.getBoundingClientRect().top;
    el.style.position = was;
    return top;
  }

  // The scroll box the page is read in, when it is not the window itself.
  function scrollBoxOf(el) {
    for (var n = el.parentElement; n; n = n.parentElement) {
      var o = getComputedStyle(n).overflowY;
      if ((o === 'auto' || o === 'scroll') && n.scrollHeight > n.clientHeight) return n;
    }
    return null;
  }

  function initTabs(list) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    function enabled() { return tabs.filter(function (t) { return !t.disabled; }); }
    function select(tab, focus, chosen) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute('aria-selected', String(on));
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
      reveal(tab);
      if (chosen) start();
    }
    // A person chose a tab (not the first paint): its panel starts at its top, and the scroll of the tab before does
    // not stay. When the top of the screen is below the top edge of the tabs (the page was scrolled into a long panel,
    // with the list out of view or stuck to the top), the page scrolls so the list is at the top of the screen, always
    // at the same height. When the top of the screen is above that edge, nothing moves.
    function start() {
      var anchor = stickyOf(list) || list;
      var edge = flowTop(anchor);
      if (edge >= 0) return;
      var room = parseFloat(getComputedStyle(anchor).scrollMarginTop) || 0;
      (scrollBoxOf(anchor) || window).scrollBy({ top: edge - room });
    }
    // The list scrolls sideways when the tabs do not fit: bring the tab into view without moving the page.
    function reveal(tab) {
      var l = list.getBoundingClientRect(), t = tab.getBoundingClientRect(), room = 6;
      var delta = t.left < l.left + room ? t.left - l.left - room : (t.right > l.right - room ? t.right - l.right + room : 0);
      if (delta) list.scrollBy({ left: delta });
    }
    list.addEventListener('click', function (e) {
      var tab = e.target.closest('[role="tab"]');
      if (tab && !tab.disabled) select(tab, false, true);
    });
    list.addEventListener('keydown', function (e) {
      var list_ = enabled();
      var i = list_.indexOf(document.activeElement);
      if (i < 0) return;
      var target;
      if (e.key === 'ArrowRight') target = list_[(i + 1) % list_.length];
      else if (e.key === 'ArrowLeft') target = list_[(i - 1 + list_.length) % list_.length];
      else if (e.key === 'Home') target = list_[0];
      else if (e.key === 'End') target = list_[list_.length - 1];
      if (target) { e.preventDefault(); select(target, true, true); }
    });
    select(enabled().filter(function (t) { return t.getAttribute('aria-selected') === 'true'; })[0] || enabled()[0]);
  }

  // Brazilian field. The mask is written while you type and the caret stays after the character you typed. The check
  // runs when you leave the field, and an error goes away as soon as the value is valid again, so nobody is told off in
  // the middle of typing. Without this script the field is a plain text field: check the value on the server too.
  var DDD = '11 12 13 14 15 16 17 18 19 21 22 24 27 28 31 32 33 34 35 37 38 41 42 43 44 45 46 47 48 49 51 53 54 55 61 62 63 64 65 66 67 68 69 71 73 74 75 77 79 81 82 83 84 85 86 87 88 89 91 92 93 94 95 96 97 98 99'.split(' ');
  // '#' is a slot. The punctuation between slots is written only once the slot after it has a character.
  var MASKS = {
    cpf: function () { return '###.###.###-##'; },
    cnpj: function () { return '##.###.###/####-##'; },
    cep: function () { return '#####-###'; },
    phone: function (c) { return c.length > 10 ? '(##) #####-####' : '(##) ####-####'; },
    date: function () { return '##/##/####'; }
  };
  var SIZE = { cpf: 11, cnpj: 14, cep: 8, phone: 11, date: 8 };
  // The characters that carry the value. The rest is mask, and the caret is placed by counting these.
  function significant(type) { return type === 'cnpj' ? /[0-9A-Za-z]/ : type === 'money' ? /[\d,]/ : /\d/; }

  // The characters of the value, without the mask. A CNPJ has letters in its first 12 places since July 2026 (the two
  // check digits stay numbers). A phone pasted with +55 loses the country code.
  function chars(type, value) {
    var c = '';
    String(value).toUpperCase().split('').forEach(function (ch) {
      if (type === 'cnpj' ? (c.length < 12 ? /[0-9A-Z]/ : /\d/).test(ch) : /\d/.test(ch)) c += ch;
    });
    if (type === 'phone' && c.length > 11 && c.slice(0, 2) === '55') c = c.slice(2);
    return c.slice(0, SIZE[type]);
  }

  // Reais: the last comma is the decimal point and dots are thousands. A pasted 1234.56 (one dot, then one or two
  // digits) is read as decimals too.
  function money(value, done) {
    var v = String(value).replace(/R\$|\s/g, '');
    if (v.indexOf(',') < 0 && /^[^.]*\.\d{1,2}$/.test(v)) v = v.replace('.', ',');
    var comma = v.indexOf(',');
    var whole = (comma < 0 ? v : v.slice(0, comma)).replace(/\D/g, '').replace(/^0+(?=\d)/, '');
    var cents = comma < 0 ? '' : v.slice(comma + 1).replace(/\D/g, '').slice(0, 2);
    if (!whole && comma < 0) return '';
    if (done) { whole = whole || '0'; cents = (cents + '00').slice(0, 2); }
    return 'R$ ' + (whole || '0').replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (done || comma >= 0 ? ',' + cents : '');
  }

  // The value with its mask. `done` is for when the person left the field: an amount gets its two decimals.
  function format(type, value, done) {
    if (type === 'money') return money(value, done);
    var c = chars(type, value), mask = MASKS[type](c), out = '', i = 0;
    for (var p = 0; p < mask.length && i < c.length; p++) out += mask[p] === '#' ? c[i++] : mask[p];
    return out;
  }

  function digitsOk(c, weights) {
    var sum = 0;
    for (var i = 0; i < weights.length; i++) sum += (c.charCodeAt(i) - 48) * weights[i];
    var r = sum % 11;
    return String(r < 2 ? 0 : 11 - r) === c[weights.length];
  }

  // '' when the value is valid or empty, 'incomplete' when it is short, 'invalid' when it cannot exist.
  function check(type, value) {
    if (type === 'money') return '';
    var c = chars(type, value);
    if (!c) return '';
    if (c.length < (type === 'phone' ? 10 : SIZE[type])) return 'incomplete';
    if (type === 'cpf') {
      return /^(\d)\1+$/.test(c) || !digitsOk(c, [10, 9, 8, 7, 6, 5, 4, 3, 2]) || !digitsOk(c, [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]) ? 'invalid' : '';
    }
    if (type === 'cnpj') {
      return /^(.)\1+$/.test(c) || !digitsOk(c, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) || !digitsOk(c, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]) ? 'invalid' : '';
    }
    if (type === 'phone') {
      // A mobile number has 11 digits and starts with 9 after the area code; a landline has 10 and starts with 2 to 5.
      return DDD.indexOf(c.slice(0, 2)) < 0 || (c.length === 11 ? c[2] !== '9' : !/[2-5]/.test(c[2])) ? 'invalid' : '';
    }
    if (type === 'date') {
      var d = +c.slice(0, 2), m = +c.slice(2, 4), y = +c.slice(4), t = new Date(y, m - 1, d);
      return y < 1000 || t.getFullYear() !== y || t.getMonth() !== m - 1 || t.getDate() !== d ? 'invalid' : '';
    }
    return '';
  }

  // The value to store or send: digits (a CNPJ in capitals), a date as yyyy-mm-dd, an amount as 1234.56. '' when the
  // value is not valid.
  function clean(type, value) {
    if (type === 'money') return money(value, true).replace(/R\$ |\./g, '').replace(',', '.');
    var c = chars(type, value);
    if (!c || check(type, value)) return '';
    return type === 'date' ? c.slice(4) + '-' + c.slice(2, 4) + '-' + c.slice(0, 2) : c;
  }

  var MESSAGES = {
    pt: {
      cpf: ['O CPF tem 11 números. Confira se falta algum.', 'Esses números não formam um CPF válido. Confira se algum foi trocado.'],
      cnpj: ['O CNPJ tem 14 caracteres. Confira se falta algum.', 'Esses caracteres não formam um CNPJ válido. Confira se algum foi trocado.'],
      cep: ['O CEP tem 8 números. Confira se falta algum.'],
      phone: ['Digite o DDD e o número, com 10 ou 11 dígitos.', 'Esse número não existe no Brasil. Confira o DDD e o primeiro dígito.'],
      date: ['Digite o dia, o mês e o ano: dd/mm/aaaa.', 'Essa data não existe. Confira o dia e o mês.']
    },
    en: {
      cpf: ['A CPF has 11 digits. Check if one is missing.', 'These digits do not make a valid CPF. Check if one was swapped.'],
      cnpj: ['A CNPJ has 14 characters. Check if one is missing.', 'These characters do not make a valid CNPJ. Check if one was swapped.'],
      cep: ['A CEP has 8 digits. Check if one is missing.'],
      phone: ['Type the area code and the number, 10 or 11 digits.', 'This number does not exist in Brazil. Check the area code and the first digit.'],
      date: ['Type the day, the month and the year: dd/mm/yyyy.', 'This date does not exist. Check the day and the month.']
    }
  };

  function langOf(el) {
    return ((el.closest('[lang]') || document.documentElement).lang || '').slice(0, 2) === 'pt' ? 'pt' : 'en';
  }

  // The message goes in the first span of the helper (the first id of aria-describedby). The helper text it replaces
  // comes back when the value is valid; a page that renders an error on the server puts that text in data-aipim-help.
  // An empty message clears the error.
  function setError(input, message) {
    var help = document.getElementById((input.getAttribute('aria-describedby') || '').split(' ')[0]);
    var span = help && help.querySelector('span');
    if (message) {
      input.setAttribute('aria-invalid', 'true');
      if (span) {
        if (!span.hasAttribute('data-aipim-help')) span.setAttribute('data-aipim-help', span.textContent);
        span.textContent = message;
      }
    } else if (input.getAttribute('aria-invalid') === 'true') {
      input.removeAttribute('aria-invalid');
      if (span && span.hasAttribute('data-aipim-help')) {
        span.textContent = span.getAttribute('data-aipim-help');
        span.removeAttribute('data-aipim-help');
      }
    }
  }

  function showError(input, kind) {
    var type = input.getAttribute('data-aipim-format');
    setError(input, kind && (input.getAttribute('data-aipim-error-' + kind) ||
      (kind === 'range' ? rangeMessage(input) : MESSAGES[langOf(input)][type][kind === 'incomplete' ? 0 : 1])));
  }

  // A date field may take data-aipim-min and data-aipim-max (yyyy-mm-dd). A valid date outside them is a 'range' error.
  function isoDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    return m ? new Date(+m[1], m[2] - 1, +m[3]) : null;
  }
  function limits(input) {
    return { min: isoDate(input.getAttribute('data-aipim-min')), max: isoDate(input.getAttribute('data-aipim-max')) };
  }
  function outOfRange(input, day) {
    var l = limits(input);
    return !!day && ((l.min && day < l.min) || (l.max && day > l.max));
  }
  function rangeMessage(input) {
    var l = limits(input), pt = langOf(input) === 'pt';
    var a = l.min && format('date', digitsOf(l.min)), b = l.max && format('date', digitsOf(l.max));
    if (a && b) return pt ? 'Escolha uma data entre ' + a + ' e ' + b + '.' : 'Choose a date between ' + a + ' and ' + b + '.';
    if (a) return pt ? 'Escolha uma data a partir de ' + a + '.' : 'Choose a date on or after ' + a + '.';
    return pt ? 'Escolha uma data até ' + b + '.' : 'Choose a date on or before ' + b + '.';
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  // ddmmyyyy, the characters of a date field, from a Date.
  function digitsOf(day) { return pad(day.getDate()) + pad(day.getMonth() + 1) + day.getFullYear(); }

  function brField(el) {
    var type = el && el.matches && el.matches('input[data-aipim-format]') && el.getAttribute('data-aipim-format');
    return type === 'money' || SIZE.hasOwnProperty(type);
  }

  // Writes the formatted value and puts the caret after the same count of significant characters as in `raw`.
  function apply(input, raw, caret) {
    var type = input.getAttribute('data-aipim-format'), sig = significant(type);
    var before = raw.slice(0, caret).split('').filter(function (ch) { return sig.test(ch); }).length;
    var value = format(type, raw), at = 0;
    for (var n = 0; at < value.length && n < before; at++) if (sig.test(value[at])) n++;
    input.value = value;
    if (document.activeElement === input) input.setSelectionRange(at, at);
    if (!check(type, value) && !(type === 'date' && outOfRange(input, isoDate(clean(type, value))))) showError(input, '');
  }

  // Deleting a dot or a dash would only bring it back with the next mask: delete the character next to it instead.
  document.addEventListener('beforeinput', function (e) {
    var input = e.target, back = e.inputType === 'deleteContentBackward';
    if (!brField(input) || !(back || e.inputType === 'deleteContentForward') || input.selectionStart !== input.selectionEnd) return;
    var v = input.value, sig = significant(input.getAttribute('data-aipim-format')), i = back ? input.selectionStart - 1 : input.selectionStart;
    if (i < 0 || i >= v.length || sig.test(v[i])) return;
    while (i >= 0 && i < v.length && !sig.test(v[i])) i += back ? -1 : 1;
    e.preventDefault();
    if (i < 0 || i >= v.length) return;
    apply(input, v.slice(0, i) + v.slice(i + 1), i);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  document.addEventListener('input', function (e) {
    if (brField(e.target)) apply(e.target, e.target.value, e.target.selectionStart);
  });
  // Leaving the field, not `change`: Safari fires no change event once a script has written the value while typing.
  // Only a value that changed is checked, so an error from the server stays when the person just passes by.
  var valueOnFocus = null;
  document.addEventListener('focusin', function (e) {
    if (brField(e.target)) valueOnFocus = e.target.value;
  });
  document.addEventListener('focusout', function (e) {
    var input = e.target;
    if (!brField(input) || input.value === valueOnFocus) return;
    var type = input.getAttribute('data-aipim-format');
    input.value = format(type, input.value, true);
    var kind = check(type, input.value);
    if (!kind && type === 'date' && outOfRange(input, isoDate(clean(type, input.value)))) kind = 'range';
    showError(input, kind);
  });

  // Combobox (ARIA 1.2, list autocomplete, chosen by hand). Focus stays in the input and aria-activedescendant names the
  // option under the arrows, so a screen reader reads it without leaving the field. Typing filters the options without
  // caring for accents or capitals ("sao" finds "São Paulo", "sp" finds the option whose data-value is SP). Enter or a
  // click chooses; Escape closes the list and, with the list closed, clears the field. A text that is not one of the
  // options shows the error when the person leaves. Without this script the field is a plain text field.
  var COMBO = {
    pt: { invalid: 'Escolha uma das opções da lista. Digite parte do nome para encontrar.', cleared: 'Campo limpo', count: function (n) { return n === 1 ? '1 opção' : n + ' opções'; } },
    en: { invalid: 'Choose one of the options in the list. Type part of the name to find it.', cleared: 'Field cleared', count: function (n) { return n === 1 ? '1 option' : n + ' options'; } }
  };
  function fold(s) { return String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); }

  function initCombobox(input) {
    var field = input.closest('.aipim-combobox') || input.parentNode;
    // The list is looked for inside the field first: Aipim.init may run on content not yet added to the page.
    var id = input.getAttribute('aria-controls');
    var list = field.querySelector('[id="' + id + '"]') || document.getElementById(id);
    // Aipim.init can run again on the same content: set each combobox up once.
    if (!list || input.hasAttribute('data-aipim-ready')) return;
    input.setAttribute('data-aipim-ready', '');
    var popup = list.closest('.aipim-combobox__popup') || list;
    var empty = popup.querySelector('.aipim-combobox__empty');
    // The value to send: the data-value of the option chosen, in a hidden input of the field, when there is one.
    var store = field.querySelector('input[type="hidden"]');
    var words = COMBO[langOf(input)];
    var options = Array.prototype.slice.call(list.querySelectorAll('[role="option"]'));
    options.forEach(function (o, i) { if (!o.id) o.id = list.id + '-' + i; });
    // The count of options found, read by a screen reader after a pause in the typing (not at every key).
    var status = document.createElement('span'), timer;
    status.className = 'aipim-visually-hidden';
    status.setAttribute('role', 'status');
    field.appendChild(status);

    function label(o) { return o.textContent.trim(); }
    function shown() { return options.filter(function (o) { return !o.hidden; }); }
    function match(text) {
      var q = fold(text);
      return q ? options.filter(function (o) { return fold(label(o)) === q || fold(o.getAttribute('data-value') || '') === q; })[0] : null;
    }
    function filter(text) {
      var q = fold(text);
      options.forEach(function (o) {
        o.hidden = !!q && fold(label(o)).indexOf(q) < 0 && fold(o.getAttribute('data-value') || '') !== q;
      });
      var n = shown().length;
      if (empty) empty.hidden = n > 0;
      clearTimeout(timer);
      timer = setTimeout(function () { status.textContent = words.count(n); }, 500);
    }
    function activate(o) {
      options.forEach(function (x) { if (x === o) x.setAttribute('aria-selected', 'true'); else x.removeAttribute('aria-selected'); });
      if (!o) { input.removeAttribute('aria-activedescendant'); return; }
      input.setAttribute('aria-activedescendant', o.id);
      // Keep it in view inside the popup, which scrolls on its own; the page does not move.
      if (o.offsetTop < popup.scrollTop) popup.scrollTop = o.offsetTop;
      else if (o.offsetTop + o.offsetHeight > popup.scrollTop + popup.clientHeight) popup.scrollTop = o.offsetTop + o.offsetHeight - popup.clientHeight;
    }
    function active() { return document.getElementById(input.getAttribute('aria-activedescendant') || ''); }
    function isOpen() { return !popup.hidden; }
    // Opened with the arrows or a click, the list shows every option, with the one already chosen under the arrows.
    function open(all) {
      if (all) filter('');
      popup.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }
    function close() {
      popup.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      activate(null);
    }
    function choose(o) {
      input.value = label(o);
      if (store) store.value = o.getAttribute('data-value') || label(o);
      close();
      setError(input, '');
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    function step(by) {
      var all = shown();
      if (!all.length) return;
      var i = all.indexOf(active());
      activate(all[i < 0 ? (by > 0 ? 0 : all.length - 1) : (i + by + all.length) % all.length]);
    }

    input.addEventListener('input', function () {
      if (store) store.value = '';
      filter(input.value);
      open(false);
      activate(null);
    });
    input.addEventListener('click', function () {
      if (isOpen()) { close(); return; }
      open(true);
      activate(match(input.value));
    });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!isOpen()) {
          open(true);
          // Alt+Down only opens. Down starts at the option chosen or the first one, Up at the last one.
          if (!e.altKey) activate(match(input.value) || (e.key === 'ArrowDown' ? shown()[0] : shown()[shown().length - 1]));
        } else if (e.altKey && e.key === 'ArrowUp') {
          if (active()) choose(active()); else close();
        } else {
          step(e.key === 'ArrowDown' ? 1 : -1);
        }
      } else if (e.key === 'Enter' && isOpen() && active()) {
        e.preventDefault();
        choose(active());
      } else if (e.key === 'Escape') {
        // Stops a modal around the field from closing too.
        if (isOpen()) { e.preventDefault(); e.stopPropagation(); close(); } else if (input.value) {
          e.preventDefault();
          input.value = '';
          if (store) store.value = '';
          filter('');
          // The script cleared the field, so a screen reader would not know: say it, in place of the count.
          clearTimeout(timer);
          status.textContent = words.cleared;
        }
      } else if (e.key === 'Tab') {
        close();
      }
    });
    // A press on an option keeps the focus in the input, so the list does not close before the click.
    popup.addEventListener('mousedown', function (e) { e.preventDefault(); });
    list.addEventListener('click', function (e) {
      var o = e.target.closest('[role="option"]');
      if (o) choose(o);
    });
    input.addEventListener('blur', function () {
      close();
      if (!input.value.trim()) { setError(input, ''); return; }
      // A text typed in full, in any case or without accents, is the option itself.
      var o = match(input.value);
      if (o) {
        input.value = label(o);
        if (store) store.value = o.getAttribute('data-value') || label(o);
        setError(input, '');
      } else {
        setError(input, input.getAttribute('data-aipim-error-invalid') || words.invalid);
      }
    });
  }

  // Date picker (ARIA date picker dialog). Typing stays the main way in: the field is the Brazilian date field, and the
  // button next to it opens a calendar written here. The arrows move by day and week, Home and End to the start and end
  // of the week, Page Up and Page Down by month (with Shift, by year); Enter or Space chooses, Escape closes. Tab stays
  // inside the calendar, and focus goes back to the button when it closes. The week starts on Sunday, and the names of
  // the months and days come from Intl in the language of the page. Without this script the button stays hidden.
  var DATE = {
    pt: { dialog: 'Escolher data', prev: 'Mês anterior', next: 'Próximo mês', selected: 'selecionado' },
    en: { dialog: 'Choose date', prev: 'Previous month', next: 'Next month', selected: 'selected' }
  };
  var calendarCount = 0;
  // Writes an attribute only when its value changes; null removes it.
  function put(el, name, value) {
    if (value === null) { if (el.hasAttribute(name)) el.removeAttribute(name); } else if (el.getAttribute(name) !== value) el.setAttribute(name, value);
  }
  function sameDay(a, b) { return !!a && !!b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
  function addDays(day, n) { return new Date(day.getFullYear(), day.getMonth(), day.getDate() + n); }
  // The same day in another month, or the last day of that month when it is shorter (31 January + 1 month = 28 February).
  function addMonths(day, n) {
    var last = new Date(day.getFullYear(), day.getMonth() + n + 1, 0).getDate();
    return new Date(day.getFullYear(), day.getMonth() + n, Math.min(day.getDate(), last));
  }

  function initDatepicker(button) {
    var field = button.closest('.aipim-datepicker');
    var input = field && field.querySelector('input[data-aipim-format="date"]');
    if (!input || field.hasAttribute('data-aipim-ready')) return;
    field.setAttribute('data-aipim-ready', '');
    var lang = langOf(input), words = DATE[lang], locale = lang === 'pt' ? 'pt-BR' : 'en';
    var longDate = new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    var monthName = new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' });
    var dayName = new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'long' });
    // The day of the week of a valid date goes on a line of its own in the helper text, so a person who meant Friday and
    // typed the 21st sees it without opening the calendar.
    var help = document.getElementById((input.getAttribute('aria-describedby') || '').split(' ')[0]);
    var weekday = null;
    if (help) {
      weekday = document.createElement('span');
      weekday.className = 'aipim-datepicker__weekday';
      weekday.hidden = true;
      help.appendChild(weekday);
    }
    var label = button.getAttribute('aria-label') || '';
    // The icons of the calendar come from the same sprite as the icon of the button.
    var use = button.querySelector('use');
    var sprite = ((use && (use.getAttribute('href') || use.getAttribute('xlink:href'))) || '').split('#')[0];
    // From the id of the field, or a number when it has none, so two calendars never share an id.
    var id = (input.id || 'aipim-date-' + (++calendarCount)) + '-calendar';

    function iconButton(cls, name, text) {
      return '<button type="button" class="aipim-icon-button ' + cls + '" aria-label="' + text + '">' +
        '<svg class="aipim-icon" aria-hidden="true"><use href="' + sprite + name + '"></use></svg></button>';
    }
    var popup = document.createElement('div');
    popup.className = 'aipim-datepicker__popup';
    popup.id = id;
    popup.hidden = true;
    popup.setAttribute('role', 'dialog');
    popup.setAttribute('aria-modal', 'true');
    popup.setAttribute('aria-label', words.dialog);
    // Sunday, 4 January 1970, starts the row of week days.
    var heads = '';
    for (var w = 0; w < 7; w++) {
      var wd = new Date(1970, 0, 4 + w);
      heads += '<th scope="col" abbr="' + wd.toLocaleDateString(locale, { weekday: 'long' }) + '">' +
        wd.toLocaleDateString(locale, { weekday: 'short' }).replace(/\.$/, '') + '</th>';
    }
    var rows = '';
    // Every day keeps tabindex="-1" for good and the focus is moved by the script. With a roving tabindex (the day that can
    // be tabbed to changing as the focus arrives) VoiceOver in Safari said nothing on most arrow presses: the attribute
    // changing on the very element being focused loses the announcement. Tab inside the dialog is handled below, so no day
    // needs to be in the tab order.
    for (var r = 0; r < 6; r++) rows += '<tr>' + new Array(8).join('<td><button type="button" tabindex="-1" hidden></button></td>') + '</tr>';
    popup.innerHTML = '<div class="aipim-datepicker__header">' +
      iconButton('aipim-datepicker__prev', '#aipim-chevron-left', words.prev) +
      '<p class="aipim-datepicker__month" id="' + id + '-month" aria-live="polite"></p>' +
      iconButton('aipim-datepicker__next', '#aipim-chevron-right', words.next) +
      '</div><table class="aipim-datepicker__grid" role="grid" aria-labelledby="' + id + '-month"><thead><tr>' + heads +
      '</tr></thead><tbody>' + rows + '</tbody></table>';
    button.after(popup);
    button.setAttribute('aria-haspopup', 'dialog');
    button.setAttribute('aria-expanded', 'false');
    button.setAttribute('aria-controls', id);
    var prev = popup.querySelector('.aipim-datepicker__prev'), next = popup.querySelector('.aipim-datepicker__next');
    var title = popup.querySelector('.aipim-datepicker__month');
    // Each day is a gridcell (the td) that holds a button, and the button takes the focus: a screen reader announces a button
    // by its name every time the focus lands on it, which it did not always do for a td with an aria-label.
    var cells = Array.prototype.slice.call(popup.querySelectorAll('tbody td'));
    var days = Array.prototype.slice.call(popup.querySelectorAll('tbody button'));
    // The day that has the focus (or would have it) in the grid. Its month is the one shown.
    var cursor = null, shownMonth = -1;

    function chosen() { return isoDate(clean('date', input.value)); }
    // The button says the date chosen, so a screen reader hears it without opening the calendar.
    function sayDate() {
      var d = chosen();
      button.setAttribute('aria-label', d ? label + ', ' + longDate.format(d) : label);
      if (weekday) {
        var shown = !!d && !outOfRange(input, d);
        weekday.hidden = !shown;
        weekday.textContent = shown ? dayName.format(d) : '';
      }
    }
    function cellOf(day) { return days.filter(function (c) { return c.dayRef && sameDay(c.dayRef, day); })[0]; }
    function render() {
      var first = new Date(cursor.getFullYear(), cursor.getMonth(), 1), start = addDays(first, -first.getDay());
      var today = new Date(), pick = chosen();
      if (shownMonth !== cursor.getFullYear() * 12 + cursor.getMonth()) {
        shownMonth = cursor.getFullYear() * 12 + cursor.getMonth();
        title.textContent = monthName.format(first);
      }
      // Only what changed is written. Taking the role or the text off a cell and putting it back, even within the same
      // instant, makes a screen reader drop the cell and say nothing when the focus lands on it.
      cells.forEach(function (td, i) {
        var c = days[i], day = addDays(start, i), inMonth = day.getMonth() === first.getMonth();
        var on = inMonth && sameDay(day, pick);
        // Days of the months around stay as empty cells, so each column is still a day of the week.
        c.dayRef = inMonth ? day : null;
        var text = inMonth ? String(day.getDate()) : '';
        if (c.textContent !== text) c.textContent = text;
        if (c.hidden === inMonth) c.hidden = !inMonth;
        put(td, 'role', inMonth ? 'gridcell' : null);
        put(td, 'aria-selected', on ? 'true' : null);
        put(c, 'class', inMonth ? 'aipim-datepicker__day' : null);
        put(c, 'aria-label', inMonth ? longDate.format(day) + (on ? ', ' + words.selected : '') : null);
        put(c, 'aria-current', inMonth && sameDay(day, today) ? 'date' : null);
        put(c, 'aria-disabled', inMonth && outOfRange(input, day) ? 'true' : null);
      });
      // A month that fits in five weeks has no sixth row.
      Array.prototype.forEach.call(popup.querySelectorAll('tbody tr'), function (row) {
        row.hidden = !row.querySelector('.aipim-datepicker__day');
      });
    }
    function moveTo(day, focus) {
      cursor = day;
      render();
      if (focus) cellOf(cursor).focus();
    }
    function isOpen() { return !popup.hidden; }
    function open() {
      // The calendar opens on the date in the field, or today, or the nearest day allowed.
      var l = limits(input), day = chosen() || new Date();
      day = new Date(day.getFullYear(), day.getMonth(), day.getDate());
      if (l.min && day < l.min) day = l.min;
      if (l.max && day > l.max) day = l.max;
      popup.hidden = false;
      button.setAttribute('aria-expanded', 'true');
      moveTo(day, true);
    }
    function close(focus) {
      if (!isOpen()) return;
      popup.hidden = true;
      button.setAttribute('aria-expanded', 'false');
      if (focus) button.focus();
    }
    function choose(day) {
      if (outOfRange(input, day)) return;
      input.value = format('date', digitsOf(day));
      setError(input, '');
      sayDate();
      close(true);
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    button.addEventListener('click', function () { if (isOpen()) close(true); else open(); });
    prev.addEventListener('click', function () { moveTo(addMonths(cursor, -1), false); });
    next.addEventListener('click', function () { moveTo(addMonths(cursor, 1), false); });
    popup.addEventListener('click', function (e) {
      var c = e.target.closest('.aipim-datepicker__day');
      if (c) choose(c.dayRef);
    });
    popup.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        // Stops a modal around the field from closing too.
        e.preventDefault();
        e.stopPropagation();
        close(true);
        return;
      }
      if (e.key === 'Tab') {
        // The buttons of the header and the day with the focus are the stops; Tab goes round them.
        var stops = [prev, next, cellOf(cursor)], i = stops.indexOf(document.activeElement);
        e.preventDefault();
        stops[(i + (e.shiftKey ? -1 : 1) + stops.length) % stops.length].focus();
        return;
      }
      var c = e.target.closest('.aipim-datepicker__day');
      if (!c) return;
      var day = c.dayRef, to = null;
      if (e.key === 'ArrowRight') to = addDays(day, 1);
      else if (e.key === 'ArrowLeft') to = addDays(day, -1);
      else if (e.key === 'ArrowDown') to = addDays(day, 7);
      else if (e.key === 'ArrowUp') to = addDays(day, -7);
      else if (e.key === 'Home') to = addDays(day, -day.getDay());
      else if (e.key === 'End') to = addDays(day, 6 - day.getDay());
      else if (e.key === 'PageUp') to = addMonths(day, e.shiftKey ? -12 : -1);
      else if (e.key === 'PageDown') to = addMonths(day, e.shiftKey ? 12 : 1);
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(day); return; }
      if (to) { e.preventDefault(); moveTo(to, true); }
    });
    // A click outside closes the calendar and leaves the focus where the click put it.
    document.addEventListener('pointerdown', function (e) {
      if (isOpen() && !popup.contains(e.target) && !button.contains(e.target)) close(false);
    });
    input.addEventListener('input', sayDate);
    input.addEventListener('change', sayDate);
    if (input.disabled || input.readOnly) button.disabled = true;
    sayDate();
  }

  document.addEventListener('click', function (e) {
    var d = e.target.closest('[data-aipim-dismiss]');
    if (d) { dismiss(d); return; }
    if ('commandForElement' in HTMLButtonElement.prototype) return;
    var b = e.target.closest('button[commandfor]');
    if (!b) return;
    var target = document.getElementById(b.getAttribute('commandfor'));
    var command = b.getAttribute('command');
    if (!target) return;
    if (command === 'show-modal' && target.showModal) target.showModal();
    else if (command === 'close' && target.close) target.close();
  });

  function init(root) {
    var scope = root && root.querySelectorAll ? root : document;
    Array.prototype.forEach.call(scope.querySelectorAll('.aipim-tabs[role="tablist"]'), initTabs);
    Array.prototype.forEach.call(scope.querySelectorAll('input[role="combobox"][aria-controls]'), initCombobox);
    // A value that came with the page gets its mask. An error rendered on the server stays until the value changes.
    Array.prototype.forEach.call(scope.querySelectorAll('input[data-aipim-format]'), function (input) {
      if (brField(input) && input.value) input.value = format(input.getAttribute('data-aipim-format'), input.value, true);
    });
    // After the mask, so the button reads the date already formatted.
    Array.prototype.forEach.call(scope.querySelectorAll('.aipim-datepicker__button'), initDatepicker);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); });
  else init();
  // For content added after load (single-page apps, Storybook): Aipim.init(container) sets up the tabs inside it.
  // Aipim.br: format(type, value, done), check(type, value) and clean(type, value) of the Brazilian field.
  window.Aipim = { init: init, br: { format: format, check: check, clean: clean } };
})();
