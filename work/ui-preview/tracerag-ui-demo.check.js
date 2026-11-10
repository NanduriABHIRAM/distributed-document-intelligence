
(() => {
  const root = document.getElementById('tracerag-preview');
  const toggle = root.querySelector('#tr-theme-toggle');
  const label = root.querySelector('#tr-theme-label');
  const status = root.querySelector('#tr-preview-status');
  const saved = window.openai?.widgetState;
  const state = { dark: saved?.modelContent?.appearance === 'dark', accent: '#23685c' };
  function render() {
    root.dataset.appearance = state.dark ? 'dark' : 'light';
    root.style.setProperty('--tr-accent', state.dark ? '#a8cdbb' : state.accent);
    toggle.setAttribute('aria-pressed', String(state.dark));
    label.textContent = state.dark ? 'Light mode' : 'Dark mode';
    status.textContent = state.dark ? 'Dark appearance' : 'Light appearance';
  }
  toggle.addEventListener('click', () => {
    state.dark = !state.dark;
    render();
    if (window.openai?.setWidgetState) {
      window.openai.setWidgetState({ modelContent: { appearance: state.dark ? 'dark' : 'light' }, privateContent: {} }).catch(() => {});
    }
  });
  root.querySelectorAll('[data-open-source]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault();
    const detail = root.querySelector('#' + link.dataset.openSource);
    detail.open = true;
    detail.querySelector('summary').focus();
  }));
  root.querySelector('#tr-run-sample').addEventListener('click', () => {
    root.querySelector('#tr-source-one').open = true;
    root.querySelector('#tr-source-two').open = true;
    status.textContent = 'Sample answer · 2 source passages';
  });
  window.addEventListener('openai:set_globals', event => {
    const incoming = event.detail?.globals?.widgetState?.modelContent?.appearance;
    if (incoming === 'light' || incoming === 'dark') { state.dark = incoming === 'dark'; render(); }
  });
  render();
  if (globalThis.Tweak) {
    const tweak = new Tweak({ container: root, onChange: render });
    tweak.addColorPicker(state, 'accent', { label: 'Light-mode accent', reference: '--tr-accent' });
  }
})();
