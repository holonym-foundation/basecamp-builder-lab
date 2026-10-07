(() => {
  const key = 'basecamp-runtime-port';
  const valid = value => ['8788', '8789'].includes(String(value));
  const saved = () => { try { return localStorage.getItem(key); } catch { return null; } };
  function apply(value) {
    const port = valid(value) ? String(value) : '8788';
    const origin = `http://127.0.0.1:${port}`;
    document.querySelectorAll('[data-runtime-port]').forEach(select => { select.value = port; });
    document.querySelectorAll('[data-runtime-address]').forEach(label => { label.textContent = origin; });
    document.querySelectorAll('a[href]').forEach(link => {
      if (/^http:\/\/(127\.0\.0\.1|localhost):878[89](\/|$)/.test(link.href)) {
        const url = new URL(link.href); url.port = port; link.href = url.href;
      }
    });
    document.querySelectorAll('[data-port-command]').forEach(command => {
      const launch = `PORT=${port} node server.mjs --open`;
      command.textContent = command.dataset.portCommand === 'mac' ? `cd ~/Downloads/sui-rebalancer && ${launch}`
        : command.dataset.portCommand === 'powershell' ? `$env:PORT="${port}"; node server.mjs --open`
        : command.dataset.portCommand === 'node24' ? `PORT=${port} npx --yes --package=node@24 -- node server.mjs --open` : launch;
    });
  }
  document.querySelectorAll('[data-runtime-port]').forEach(select => select.addEventListener('change', () => {
    if (!valid(select.value)) return;
    try { localStorage.setItem(key, select.value); } catch {}
    apply(select.value);
  }));
  addEventListener('storage', event => { if (event.key === key) apply(event.newValue); });
  apply(saved());
})();
