# Workshop registration and native SUI payouts

The participant uses the Funding screen after saving their Sui address in Strategy. They enter their email; the console submits that email and saved address together. The public Funding QR accepts the same pair directly. No attendee invite code or operator key is required.

The host uses https://sui-basecamp-funding.j94fv2pvjn.chatgpt.site/operator with their private operator key. Load controls, select Prepare registration, and leave the real window closed until the room is ready. Select Open 15-minute registration once. At most 30 unique email/address pairs are selected; later registrations are waitlisted. Repeated identical pairs return the same receipt; rebinding either identity is rejected. A registration receipt is not a payment receipt.

After cutoff, download campaign.json and responses.csv to a private folder. The paired campaign is separate from earlier code-based campaigns. Do not mix their exports. Wallet addresses are participant-provided, not an email lookup or a proof of wallet ownership; review the mapping before paying.

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

Planning is offline and sends nothing. Review every email/address pair, exclusions, network and total in the plan. It preserves the server’s waitlist, enforces the 15-minute window and 30-recipient cap, and binds the original registration fields into the confirmation hash. Legacy code campaigns still require --codes; the current email campaign does not.

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

Use Separate rehearsal campaign (testnet) in the operator screen and register.html?rehearsal=1 for form rehearsal. Console ?rehearsal=1 sends registrations to that isolated lane; it does not change the agent recipe’s mainnet read configuration. Never open the real campaign just to test a QR.

Run source tests with `python3 -m unittest -v` from this folder. Tests use injected wallet/RPC functions, not real funds. A live payout rehearsal, measured allowance and authenticated funded sender remain required before calling distribution proven.
