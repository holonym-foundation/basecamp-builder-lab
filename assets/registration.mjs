// The public form lives beside the deck. Only public intake/status use this API.
// No operator key, wallet signer, session cookie or export is part of this client.
const API = 'https://sui-basecamp-funding.j94fv2pvjn.chatgpt.site';
const rehearsal = new URLSearchParams(location.search).get('rehearsal') === '1';
const query = rehearsal ? '?rehearsal=1' : '';
const $ = id => document.getElementById(id);
let status = null, busy = false, saved = false, refreshing = false;
if (rehearsal) $('eyebrow').textContent += ' · REHEARSAL ONLY';
function render() {
  $('submit').disabled = busy || saved || status?.state !== 'open';
  $('submit-label').textContent = busy ? 'Saving…' : 'Register wallet';
  $('dot').classList.toggle('live', status?.state === 'open');
  if (!status) $('window').textContent = 'Checking registration…';
  else if (status.state === 'unavailable') $('window').textContent = 'Connection unavailable. Your registration has not been submitted.';
  else if (status.state === 'waiting') $('window').textContent = 'Registration opens when the host starts the window.';
  else if (status.state === 'closed') $('window').textContent = 'Registration has closed. You can still follow the builder guides.';
  else {
    const seconds = Math.max(0, Math.ceil((Date.parse(status.closed_at) - Date.now()) / 1000));
    // Display only: the server, not the participant's clock, enforces the cutoff.
    $('window').textContent = seconds > 0 ? `Registration open · about ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')} remaining` : 'Checking the registration cutoff…';
  }
  $('retry').hidden = status?.state !== 'unavailable';
  if (status?.network) $('network').textContent = `Use your agent wallet’s Sui ${status.network} address. No password or recovery phrase.`;
}
async function request(path, options = {}) {
  const response = await fetch(API + path + query, {credentials: 'omit', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000), ...options});
  const data = await response.json();
  if (!response.ok) throw Error(data.error || 'Could not save. Retry with the same code and address.');
  return data;
}
async function refresh() {
  if (refreshing || saved) return;
  refreshing = true;
  try {
    const next = await request('/api/status');
    if (!['waiting','open','closed'].includes(next.state) || !['mainnet','testnet'].includes(next.network) || (next.state === 'open' && !Number.isFinite(Date.parse(next.closed_at)))) throw Error('Invalid registration status');
    status = next;
  } catch { status = {state:'unavailable'}; }
  finally { refreshing = false; render(); }
}
$('retry').onclick = refresh;
$('registration').onsubmit = async event => {
  event.preventDefault();
  if (busy || saved || status?.state !== 'open') return;
  const code = $('code').value.trim().toLowerCase(), address = $('address').value.trim().toLowerCase();
  $('error').hidden = true;
  if (!/^[a-f0-9]{32}$/.test(code) || !/^0x[0-9a-f]{64}$/.test(address) || BigInt(address) <= 15n) {
    $('error').textContent = 'Check your individual workshop code and full Sui wallet address.';
    $('error').hidden = false; return;
  }
  busy = true; render();
  try {
    const data = await request('/api/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code,address})});
    if (!['selected','waitlist'].includes(data.status) || typeof data.receipt !== 'string' || !data.receipt) throw Error('Could not confirm the receipt. Retry with the same code and address.');
    saved = true;
    $('result-title').textContent = data.status === 'selected' ? 'Registration received.' : 'You’re on the waitlist.';
    $('result-message').textContent = data.status === 'selected' ? 'Your place is saved for funding review. The host will confirm the allowance after registration closes.' : 'The 30 funding places are reserved. You can still follow along with the read-only builds.';
    $('receipt').textContent = data.receipt;
    $('intake').hidden = true; $('confirmation').hidden = false; $('confirmation').focus();
  } catch (error) {
    $('error').textContent = error instanceof Error && error.message !== 'Failed to fetch' ? error.message : 'Could not confirm your registration. Retry with the same code and address.';
    $('error').hidden = false;
  } finally {busy = false; render();}
};
refresh();
setInterval(refresh, 10000);
setInterval(render, 1000);
