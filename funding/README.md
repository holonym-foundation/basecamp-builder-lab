# Workshop registration and native SUI payouts

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

Execution sends real native SUI. It checks CLI version, sender, network identity and balance; persists intent before each dispatch; and verifies each receipt before continuing. The reserve is a sender balance floor, not a hard transaction gas limit. On an uncertain outcome, stop and retain the ledger. Never create another ledger or blindly retry to work around an unresolved payment.

If the exact transaction digest is independently known, reconcile without sending:

```sh
python3 funding/payout.py reconcile --plan /PRIVATE/plan.json \
  --ledger /PRIVATE/payouts.sqlite --address FULL_RECIPIENT_ADDRESS --digest EXACT_DIGEST
python3 funding/payout.py report --plan /PRIVATE/plan.json --ledger /PRIVATE/payouts.sqlite
```

Keep the operator key, authenticated session, exports, plan and ledger private. This repository contains none of them.

## Rehearsal and evidence

Use Separate rehearsal campaign (testnet) in the operator screen and register.html?rehearsal=1 for form rehearsal. Console ?rehearsal=1 sends registrations to that isolated lane; it does not change the agent recipe’s mainnet read configuration. Keep test registrations in that rehearsal lane; the real registration accepts submissions without an open timer.

Run source tests with `python3 -m unittest -v` from this folder. Tests use injected wallet/RPC functions, not real funds. A live payout rehearsal, measured allowance and authenticated funded sender remain required before calling distribution proven.
