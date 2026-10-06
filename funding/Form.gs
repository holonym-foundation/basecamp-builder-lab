/** Paste into a private Google Apps Script project. Never publish as a web app. */
const SETTINGS = { minutes: 15, cap: 30, inviteCount: 60 };

function setupFundingForm() {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
  const p = PropertiesService.getScriptProperties();
  if (p.getProperty('formId')) throw new Error('Already created; reuse the existing form.');
  const form = FormApp.create('Sui Basecamp · Workshop funding');
  p.setProperty('formId', form.getId()); // Preserve identity even if later setup fails.
  form.setAcceptingResponses(false);
  form.setCollectEmail(false);
  form.setPublishingSummary(false);
  form.setAllowResponseEdits(false);
  form.setDescription('Enter your individual workshop code and the Sui address of your agent wallet. Registration lasts 15 minutes. Up to 30 valid, unique registrations receive the approved workshop allowance; the rest join the waitlist. Never enter a password or recovery phrase.');
  form.setConfirmationMessage('Submission received. Eligibility is confirmed after registration closes. Keep your workshop code.');
  form.setCustomClosedFormMessage('Registration is closed. You can still follow the workshop and run the read-only recipe.');
  form.addTextItem().setTitle('Workshop code').setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextMatchesPattern('^[A-Za-z0-9-]{8,64}$').build());
  form.addTextItem().setTitle('Sui wallet address').setRequired(true)
    .setHelpText('Copy your agent wallet’s Sui address: 0x followed by 64 hexadecimal characters.')
    .setValidation(FormApp.createTextValidation().requireTextMatchesPattern('^0x[0-9a-fA-F]{64}$').build());
  const folder = DriveApp.createFolder('Basecamp funding — PRIVATE');
  p.setProperty('folderId', folder.getId());
  const codes = Array.from({length: SETTINGS.inviteCount}, () => Utilities.getUuid().replace(/-/g, '').slice(0, 24));
  p.setProperty('codes', JSON.stringify(codes));
  folder.createFile('codes.csv', 'code\n' + codes.join('\n') + '\n', MimeType.CSV);
  p.setProperty('ready', 'yes');
  console.log('Participant form: ' + form.getPublishedUrl());
  console.log('Operator form: ' + form.getEditUrl());
  console.log('Private files: ' + folder.getUrl());
  } finally { lock.releaseLock(); }
}

/** Run when showing the QR. One window only; no accidental reopen. */
function openFundingWindow() {
  const lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
  const p = PropertiesService.getScriptProperties();
  if (p.getProperty('ready') !== 'yes') throw new Error('Finish setup first.');
  if (p.getProperty('openedAt')) throw new Error('This campaign already opened; cannot reopen.');
  const start = new Date();
  const end = new Date(start.getTime() + SETTINGS.minutes * 60000);
  const config = {
    campaign: Utilities.getUuid(), network: 'mainnet', cap: SETTINGS.cap,
    openedAt: start.toISOString(), closedAt: end.toISOString(),
    formUrl: FormApp.openById(p.getProperty('formId')).getPublishedUrl()
  };
  p.setProperty('openedAt', config.openedAt);
  p.setProperty('closedAt', config.closedAt);
  DriveApp.getFolderById(p.getProperty('folderId')).createFile('campaign.json', JSON.stringify(config, null, 2), MimeType.PLAIN_TEXT);
  // Triggers can run late: export/planner independently reject responses at/after end.
  ScriptApp.newTrigger('closeFundingWindow').timeBased().at(end).create();
  FormApp.openById(p.getProperty('formId')).setAcceptingResponses(true);
  console.log('Opens ' + config.openedAt + '; exact eligibility cutoff ' + config.closedAt);
  } finally { lock.releaseLock(); }
}

function closeFundingWindow() {
  FormApp.openById(PropertiesService.getScriptProperties().getProperty('formId')).setAcceptingResponses(false);
}

/** Export after cutoff. This is the only supported CSV format for the local tool. */
function exportFundingResponses() {
  const p = PropertiesService.getScriptProperties();
  const cutoff = Date.parse(p.getProperty('closedAt') || '');
  if (!Number.isFinite(cutoff) || Date.now() < cutoff) throw new Error('Wait until the 15-minute window ends.');
  closeFundingWindow();
  const quote = value => '"' + String(value).replace(/"/g, '""') + '"';
  const rows = [['response_id', 'submitted_at', 'code', 'address']];
  for (const response of FormApp.openById(p.getProperty('formId')).getResponses()) {
    const values = {};
    for (const item of response.getItemResponses()) values[item.getItem().getTitle()] = item.getResponse();
    rows.push([response.getId(), response.getTimestamp().toISOString(), values['Workshop code'] || '', values['Sui wallet address'] || '']);
  }
  const file = DriveApp.getFolderById(p.getProperty('folderId')).createFile(
    'responses-' + new Date().toISOString().replace(/:/g, '-') + '.csv',
    rows.map(row => row.map(quote).join(',')).join('\r\n') + '\r\n', MimeType.CSV);
  console.log('Download this CSV: ' + file.getUrl());
}
