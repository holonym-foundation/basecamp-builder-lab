# Workshop registration and native Sui payouts

The participant uses the Funding screen after saving their Sui address in Strategy. They enter their email; the console submits that email and saved address together. The public Funding QR accepts the same pair directly. No attendee invite code or operator key is required.

The host uses https://sui-basecamp-funding.j94fv2pvjn.chatgpt.site/operator with their private operator key. Load controls and prepare registration. The 15-minute timer is optional guidance; registration does not require the timer to start and does not reject submissions when it expires. The host can explicitly stop further registration. At most 30 unique email/address pairs are selected; later registrations are waitlisted. Repeated identical pairs return the same receipt; rebinding either identity is rejected. A registration receipt is not a payment receipt.

Download campaign.json and responses.csv to a private folder whenever you want to inspect the cohort. Use the complete export, including waitlisted rows. The paired campaign is separate from earlier code-based campaigns. Do not mix their exports. Wallet addresses are participant-provided, not an email lookup or a proof of wallet ownership; review the mapping before paying.

## Create the offline payout plan

Use Python 3.11+ and curl on macOS/Linux. Set the participant allowance, total and sender reserve after a complete recipe action is measured. The presenter’s initial rehearsal balance is not the participant allowance. Local agents do not incur an AEX deployment fee.

```sh
python3 funding/payout.py plan \
  --campaign /PRIVATE/campaign.json \
  --csv /PRIVATE/responses.csv \
  --sender FULL_SUI_ADDRESS_OF_AEX_FUNDING_ACCOUNT \
  --amount-sui MEASURED_PARTICIPANT_ALLOWANCE \
  --max-total-sui APPROVED_RECIPIENT_TOTAL \
  --gas-reserve-sui APPROVED_SENDER_RESERVE \
  --out /PRIVATE/plan.json
```

Planning is offline and sends nothing. Review every email/address pair, exclusions, network and total in the plan. For email campaign version 2 (`windowPolicy: advisory`, `selectionPolicy: first-come-first-served`), it selects the first 30 unique registered pairs using the server sequence in response IDs, preserves the waitlist, and binds every exported registration field into the confirmation hash. It verifies complete consecutive server ordering; missing rows, duplicate identities or conflicting selection statuses require a fresh export and review. Timing does not determine eligibility. Legacy code campaigns and earlier email exports retain their strict 15-minute rules and existing plan hashes. Legacy code campaigns still require --codes; the current email campaign does not.

You can preview a plan before registration ends. Before sending, settle on one reviewed cohort and preserve its exact plan and ledger. Once execution binds the campaign to that plan, a later export cannot replace it or add recipients through a new ledger. Exporting and offline planning do not send funds.

## Funding from a wallet created in the web app

The operator key unlocks registration controls only. It does not connect or authenticate a WaaP wallet. The dashboard has no sender-wallet connection or transaction approval UI yet.

A web wallet signed in with an email link, social login or passkey does not necessarily have a CLI password. The pinned CLI supports email/password login; it does not reuse the browser session. Do not run signup to access an existing funded account.

For a single rehearsal transfer, use the existing wallet at https://waap.xyz, sign in normally, select Sui on mainnet and prepare a Send to the participant's full saved Sui address. Review the amount and network in the wallet before approval. A registration receipt does not authorize a payment. Record the confirmed transaction digest; do not include an already-paid recipient in an automatic payout without reconciling that payment.

For CLI payouts from the same account:

1. In the web wallet, record the funding account's full Sui address and network.
2. If that account already has a password, use the private login launcher. Otherwise explicitly request a password setup/reset email:

```sh
WAAP_CLI_ENV=production npx --yes @human.tech/waap-cli@2.2.1 reset-password --email aex@holonym.id
```

3. Open the email and set a password through the wallet's reset page. The implementation adds a credential to the existing identity when none exists. Completing reset signs out existing sessions. This account-change step is operator initiated; the workshop tools never trigger it automatically.
4. Run the local funding-wallet sign-in launcher and enter the new password at its hidden prompt. Keep its isolated session directory. No funds move during login.
5. Check `whoami` using that session and the pinned CLI. Compare its email and full Sui address with the web wallet. Only proceed when they match and mainnet balance/gas checks pass.

The presenter completed CLI login on October 7. Its Sui sender matched the confirmed 1 Sui rehearsal funding transfer. Batch distribution has not yet been rehearsed. Never treat matching email alone as proof that the intended funded wallet is connected. The independent recipient wallet setup does not authenticate the funding account.

## Before any batch: earlier manual payments

The rehearsal wallet already received its 1 Sui. The current script cannot import an earlier manual payment into a new payout ledger: `reconcile` only resolves a dispatch that this ledger already recorded. If a selected export includes an already-paid presenter or rehearsal wallet, stop before execute and have the payout agent resolve the cohort or add an explicitly reviewed prior-payment import. Do not delete rows from the complete export or send a second payment by assumption.

## Send from the dedicated funding session

Authenticate aex@holonym.id privately with pinned @human.tech/waap-cli@2.2.1 and an isolated WAAP_CLI_SESSION_DIR. Do not use AEX coordinator buyer/seller rehearsal sessions. Keep a single durable ledger for the campaign.

```sh
export WAAP_CLI_SESSION_DIR=/PRIVATE/workshop-funding-session
python3 funding/payout.py execute \
  --plan /PRIVATE/plan.json \
  --ledger /PRIVATE/payouts.sqlite \
  --waap /ABSOLUTE/PATH/TO/PINNED/waap-cli \
  --confirm EXACT_REVIEWED_PLAN_SHA256
```

Execution sends real native Sui. It checks CLI version, sender, network identity and balance; persists intent before each dispatch; and verifies each receipt before continuing. The reserve is a sender balance floor, not a hard transaction gas limit. On an uncertain outcome, stop and retain the ledger. Never create another ledger or blindly retry to work around an unresolved payment.

If the exact transaction digest is independently known, reconcile without sending:

```sh
python3 funding/payout.py reconcile --plan /PRIVATE/plan.json \
  --ledger /PRIVATE/payouts.sqlite --address FULL_RECIPIENT_ADDRESS --digest EXACT_DIGEST
python3 funding/payout.py report --plan /PRIVATE/plan.json --ledger /PRIVATE/payouts.sqlite
```

Keep the operator key, authenticated session, exports, plan and ledger private. This repository contains none of them.

## Rehearsal and evidence

Use Separate rehearsal campaign (testnet) in the operator screen and register.html?rehearsal=1 for form rehearsal. Console ?rehearsal=1 sends registrations to that isolated lane; it does not change the agent recipe’s mainnet read configuration. Keep test registrations in that rehearsal lane; the real registration accepts submissions without an open timer.

Run source tests with `python3 -m unittest -v` from this folder. Tests use injected wallet/RPC functions, not real funds. The funding sender is authenticated and the manual 1 Sui rehearsal transfer is confirmed. A live batch payout rehearsal and measured participant allowance remain required before calling batch distribution proven.
