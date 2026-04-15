(function(){
  const KEY = 'cuidar_theme_pref'; // 'system' | 'light' | 'dark'
  const SELECTOR = '.theme-toggle';

  function getStored() {
    return localStorage.getItem(KEY) || 'system';
  }

  function store(pref) {
    localStorage.setItem(KEY, pref);
  }

  function effectiveTheme(pref) {
    if (pref === 'light' || pref === 'dark') return pref;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function apply(pref) {
    if (pref === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else if (pref === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      // system: remove explicit attribute so CSS prefers-color-scheme applies
      document.documentElement.removeAttribute('data-theme');
    }

    updateButtonState(pref);
  }

  function updateButtonState(pref) {
    const btns = document.querySelectorAll(SELECTOR);
    const eff = effectiveTheme(pref);
    const iconFor = (p) => {
      if (p === 'system') return '🌗'; // half moon for following system
      return p === 'light' ? '☀️' : '🌑'; // sun for light, new moon for dark
    };

    btns.forEach(btn => {
      btn.setAttribute('data-pref', pref);
      // set accessible label and title
      btn.setAttribute('aria-label', pref === 'system' ? `Tema: acompanhar sistema (atual: ${eff})` : `Tema: ${pref}`);
      btn.title = pref === 'system' ? `Acompanhar sistema (atual: ${eff})` : (pref === 'light' ? 'Tema claro' : 'Tema escuro');

      // update dot/icon
      const dot = btn.querySelector('.dot');
      if (dot) {
        dot.textContent = iconFor(pref);
        dot.setAttribute('aria-hidden', 'true');
      }
      btn.setAttribute('aria-pressed', eff === 'dark');
    });
  }

  function togglePref() {
    const current = getStored();
    const order = ['system','light','dark'];
    const next = order[(order.indexOf(current) + 1) % order.length];
    store(next);
    apply(next);
  }

  // Listen for system theme changes when preference is system
  const mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  function onSystemChange() {
    const pref = getStored();
    if (pref === 'system') apply('system');
  }
  if (mq && mq.addEventListener) mq.addEventListener('change', onSystemChange);
  else if (mq && mq.addListener) mq.addListener(onSystemChange);

  // Init
  document.addEventListener('DOMContentLoaded', function(){
    const stored = getStored();
    apply(stored);

    const btns = document.querySelectorAll(SELECTOR);
    btns.forEach(b => b.addEventListener('click', togglePref));
  });
})();
