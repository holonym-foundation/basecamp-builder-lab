// The public form lives beside the deck. Only public intake/status use this API.
// No operator key, wallet signer, session cookie or export is part of this client.
const API = 'https://sui-basecamp-funding.j94fv2pvjn.chatgpt.site';
const rehearsal = new URLSearchParams(location.search).get('rehearsal') === '1';
const query = '?intake=email' + (rehearsal ? '&rehearsal=1' : '');
const $ = id => document.getElementById(id);
let status = null, busy = false, saved = false, refreshing = false;
if (rehearsal) $('eyebrow').textContent += ' · REHEARSAL ONLY';
function render() {
  $('submit').disabled = busy || saved || status?.state !== 'open';
  $('submit-label').textContent = busy ? 'Saving…' : 'Register email';
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
  if (status?.network) $('network').textContent = 'Use the same email as your workshop wallet. No password or recovery phrase.';
}
async function request(path, options = {}) {
  let response, data;
  try { response = await fetch(API + path + query, {credentials: 'omit', cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000), ...options}); }
  catch { throw Error('Connection interrupted. Retry with the same email and wallet address.'); }
  try { data = await response.json(); }
  catch { throw Error('Registration service unavailable. Retry with the same email and wallet address.'); }
  if (!response.ok) throw Error(data.error || 'Could not save. Retry with the same email and wallet address.');
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
  const email = $('email').value.trim().toLowerCase(), address = $('address').value.trim().toLowerCase();
  $('error').hidden = true;
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254 || !/^0x[0-9a-f]{64}$/.test(address) || BigInt(address) <= 15n) {
    $('error').textContent = 'Enter your email and the full Sui address from wallet setup.';
    $('error').hidden = false; return;
  }
  busy = true; render();
  try {
    const data = await request('/api/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email,address})});
    if (!['selected','waitlist'].includes(data.status) || typeof data.receipt !== 'string' || !data.receipt) throw Error('Could not confirm the receipt. Retry with the same email and wallet address.');
    saved = true;
    $('result-title').textContent = data.status === 'selected' ? 'Registration received.' : 'You’re on the waitlist.';
    $('result-message').textContent = data.status === 'selected' ? 'Your email is saved for funding review. The host will confirm your wallet and allowance before sending funds.' : 'The 30 funding places are reserved. You can still follow along with the read-only builds.';
    $('receipt').textContent = data.receipt;
    $('intake').hidden = true; $('confirmation').hidden = false; $('confirmation').focus();
  } catch (error) {
    $('error').textContent = error instanceof Error && error.message !== 'Failed to fetch' ? error.message : 'Could not confirm your registration. Retry with the same email and wallet address.';
    $('error').hidden = false;
  } finally {busy = false; render();}
};
const prefill=new URLSearchParams(location.hash.slice(1)).get('address');
if(prefill&&/^0x[0-9a-fA-F]{64}$/.test(prefill))$('address').value=prefill;
refresh();
setInterval(refresh, 10000);
setInterval(render, 1000);
