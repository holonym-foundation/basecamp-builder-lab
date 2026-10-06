// Apps Script lifecycle contract with in-memory Google service doubles; no Google calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const properties = new Map();
const files = [];
const patterns = [];
let responses = [], accepting = true, now = Date.parse('2026-01-01T04:30:00Z'), trigger;
const form = {
  getId: () => 'form-id', getPublishedUrl: () => 'https://docs.google.com/forms/d/e/test/viewform',
  getEditUrl: () => 'https://docs.google.com/forms/d/test/edit',
  setAcceptingResponses: value => { accepting = value; }, getResponses: () => responses,
  setCollectEmail() {}, setPublishingSummary() {}, setAllowResponseEdits() {}, setDescription() {},
  setConfirmationMessage() {}, setCustomClosedFormMessage() {},
  addTextItem() { return { setTitle() { return this; }, setRequired() { return this; },
    setValidation() { return this; }, setHelpText() { return this; } }; }
};
const folder = {getId: () => 'folder-id', getUrl: () => 'private-folder',
  createFile(name, body) { files.push({name, body}); return {getUrl: () => 'private-export'}; }};
class Clock extends Date {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return now; }
}
let sequence = 0;
const context = vm.createContext({
  Date: Clock, console: {log() {}},
  PropertiesService: {getScriptProperties: () => ({getProperty: key => properties.get(key), setProperty: (key, value) => properties.set(key, value)})},
  LockService: {getScriptLock: () => ({waitLock() {}, releaseLock() {}})},
  FormApp: {create: () => form, openById: () => form,
    createTextValidation: () => ({requireTextMatchesPattern(pattern) {patterns.push(pattern); return this;}, build: () => ({})})},
  DriveApp: {createFolder: () => folder, getFolderById: () => folder},
  MimeType: {CSV: 'text/csv', PLAIN_TEXT: 'text/plain'},
  Utilities: {getUuid: () => (++sequence).toString(16).padStart(24, '0')+'abcdefab'},
  ScriptApp: {newTrigger: name => ({timeBased() {return this;}, at(date) {trigger = {name, date}; return this;}, create() {}})}
});
vm.runInContext(fs.readFileSync(new URL('./Form.gs', import.meta.url), 'utf8'), context);
context.setupFundingForm();
assert.equal(accepting, false);
assert.equal(files[0].body.trim().split('\n').length, 61);
assert(patterns.every(pattern => pattern.startsWith('^') && pattern.endsWith('$')));
assert.throws(() => context.setupFundingForm(), /Already created/);
context.openFundingWindow();
assert.equal(accepting, true);
const campaign = JSON.parse(files.find(f => f.name === 'campaign.json').body);
assert.equal(Date.parse(campaign.closedAt)-Date.parse(campaign.openedAt), 900000);
assert.equal(trigger.date.getTime(), now+900000);
assert.throws(() => context.openFundingWindow(), /cannot reopen/);
assert.throws(() => context.exportFundingResponses(), /Wait until/);
now += 900000;
responses = [{getId: () => 'response-1', getTimestamp: () => new Clock(now-1000),
  getItemResponses: () => [
    {getItem: () => ({getTitle: () => 'Workshop code'}), getResponse: () => 'a'.repeat(24)},
    {getItem: () => ({getTitle: () => 'Sui wallet address'}), getResponse: () => '0x'+'a'.repeat(64)}
  ]}];
context.exportFundingResponses();
assert.equal(accepting, false);
const exported = files.at(-1).body;
assert(exported.startsWith('"response_id","submitted_at","code","address"\r\n'));
assert(exported.includes('2026-01-01T04:44:59.000Z'));
console.log('Form lifecycle checks passed: private setup, 15-minute window, no reopen, cutoff export, CSV schema.');
