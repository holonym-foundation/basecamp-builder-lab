# Workshop funding: 15-minute form → private CSV → local payouts

This fallback does not require AEX. It collects **individual workshop codes and Sui addresses** in a hosted registration form, selects at most **30 valid unique registrations**, and uses the operator's WaaP CLI to send a measured allowance. Everyone else is waitlisted. No allowance is built into this kit.

The participant QR opens the form, not a wallet, payment request or claim link. The form always says submission received, not funds sent or place guaranteed. Individual invite codes are distributed privately, one per person. Duplicate codes/addresses cannot get another allocation. This does not identify humans: someone with multiple legitimately issued codes and wallets could submit multiple times; staff controls code issuance.

## 1. Prepare the hosted registration form

Use the [workshop registration page](https://holonym-foundation.github.io/basecamp-builder-lab/register.html). The [operator page](https://sui-basecamp-funding.j94fv2pvjn.chatgpt.site/operator) requires the private operator key supplied to the workshop owner. Keep this key out of links, screenshots, the deck and public files. The browser holds it only in page memory. Site audience access and this operator key are separate controls; signed-out attendee access must be verified before showing the QR.

1. Open the operator page, enter the key and select **Load private controls**. Leave **Separate rehearsal campaign** unchecked for the actual workshop.
2. Select **Prepare 60 private codes** once. Download `codes.csv` and issue one code privately to each attendee. Preparing does not open registration. Repeating preparation cannot replace the existing campaign or codes.
3. Confirm the wallet network and measured funding allowance with the host. The real campaign collects Sui mainnet addresses; the isolated rehearsal campaign uses testnet. No amount is supplied by this form, and it cannot send funds.
4. When the room is ready, show the participant QR and select **Open 15-minute registration**. Opening is operator-controlled and cannot be repeated. The server stores the opening/cutoff times and enforces the exact cutoff on every submission.
5. After the cutoff, select **Load private controls** again. Download `campaign.json` and `responses.csv`, keeping the original `codes.csv` alongside them in a private folder. **Close registration early** permanently stops further intake; it preserves the original 15-minute cutoff, and payout planning still waits until that time.

The backend atomically reserves the first 30 valid unique code/address registrations for funding review; further eligible submissions join the waitlist. Reusing the same code and address returns the original receipt. A code cannot register another address, and an address cannot reserve a second place. No submission means funds have been sent. The amount remains a separate operator decision.

For rehearsal, use the operator's **Separate rehearsal campaign** checkbox and the participant URL with `?rehearsal=1`. Rehearsal codes, addresses and exports are isolated from the actual workshop. Never open the real campaign to test the form. Each campaign opens only once.

Generate the participant QR locally:

```sh
python3 -m venv /tmp/basecamp-qr-env
/tmp/basecamp-qr-env/bin/pip install 'qrcode[pil]==8.2'
/tmp/basecamp-qr-env/bin/python funding/qr.py \
  --url 'https://holonym-foundation.github.io/basecamp-builder-lab/register.html' \
  --out /tmp/registration-qr.png
```

Use `.svg` as the output extension for a vector QR. Never encode the operator URL or key. A QR does not change site permissions or open registration.

### Optional Google Forms alternative

`Form.gs` remains a separate Google-account alternative. Do not create a second campaign if using the hosted form. In a private Apps Script project, run `setupFundingForm`, privately retain its codes, and use its published respondent URL. Run `openFundingWindow` only when showing that alternative's QR; after cutoff, run `exportFundingResponses`. Use that campaign's own codes, CSV and configuration together. Google's closing trigger may run late; the local planner enforces the exact saved cutoff. Use the helper's ISO-timestamp CSV, not Google's locale-dependent default export. Google-account setup and external respondent access require their own rehearsal.

## 2. Export and review

After the window ends, download the hosted operator page's `responses.csv`, `codes.csv` and `campaign.json` into a private local folder. Use the three files from the same campaign; never mix the hosted and Google Forms alternatives. Do not edit timestamps, IDs or the window after collection. An existing plan remains bound to its campaign in the ledger.

Choose the amount only after a complete recipe action is measured. For local agents there is no AEX deployment fee. Reserve enough sender SUI for network costs in addition to the recipient total. The reserve is a balance floor, **not a hard maximum transaction gas fee**.

With Python 3.11+ and curl on macOS/Linux:

```sh
python3 funding/payout.py plan \
  --campaign /PRIVATE/campaign.json --codes /PRIVATE/codes.csv \
  --csv /PRIVATE/responses.csv --sender YOUR_FULL_SUI_SENDER_ADDRESS \
  --amount-sui MEASURED_ALLOWANCE --max-total-sui APPROVED_RECIPIENT_TOTAL \
  --gas-reserve-sui APPROVED_SENDER_RESERVE --out /PRIVATE/plan.json
```

**Plan never connects to a wallet or sends funds.** It rejects malformed addresses, unknown codes, duplicate response IDs, out-of-window responses, duplicate codes/wallets, zero amounts and totals over the approved maximum. Review all selected addresses and exclusions in `plan.json`, not just the count. Correct an erroneous address only through an explicit operator-reviewed new plan before any dispatch. Never make a second plan/ledger to work around an uncertain payment.

## 3. Operator payout

Install/pin `@human.tech/waap-cli@2.2.1` separately, using Node 24. Log in yourself using a **dedicated workshop funding session**; never reuse AEX buyer/seller rehearsal sessions. No credentials are supplied to this kit. Keep one durable ledger for this campaign. The transfer tool operates sequentially (one independently checked receipt before the next recipient), not as one batch transaction.

```sh
export WAAP_CLI_SESSION_DIR=/PRIVATE/workshop-funding-session
# Log in privately using the CLI's password-stdin flow before execution.
python3 funding/payout.py execute \
  --plan /PRIVATE/plan.json --ledger /PRIVATE/payouts.sqlite \
  --waap /ABSOLUTE/PATH/TO/waap-cli --confirm EXACT_REVIEWED_PLAN_SHA256
```

This command **sends real funds on the network in the plan**. It verifies the CLI version, sender and RPC network identity, then checks remaining principal plus gas reserve. Each dispatch is durably recorded before invoking the CLI. Transfers require the operator's existing WaaP authorization; this tool creates no new signing authority.

Confirmed receipts must independently show the correct chain, sender, recipient SUI increase, success, checkpoint and a time after dispatch. A changed plan is rejected. A restart skips confirmed payments. An error, timeout, interrupted process or missing receipt leaves the payment unresolved and **blocks sending more**. The tool has no resend/reset command. If no transaction was actually submitted, staff must establish that independently before any recovery; the tool intentionally does not guess.

The read-only receipt verifier uses the configured public network RPCs. If a provider is unavailable or stops serving the JSON-RPC methods, it stops; it does not trust the CLI receipt alone. Validate provider availability in rehearsal before funding this flow.

## 4. Reconcile and report

If the CLI lost the response but the exact digest is independently known, reconcile without sending:

```sh
python3 funding/payout.py reconcile --plan /PRIVATE/plan.json \
  --ledger /PRIVATE/payouts.sqlite --address FULL_RECIPIENT_ADDRESS --digest EXACT_DIGEST
python3 funding/payout.py report --plan /PRIVATE/plan.json --ledger /PRIVATE/payouts.sqlite
```

Keep the plan, ledger, private form export and receipts together. Do not delete or relocate the ledger to retry. It prevents duplicate sends only when every operator uses that same ledger; manual transfers or another ledger are outside that guarantee. Preserve the sender session until any uncertain operations have been reconciled.

## Verification scope

```sh
cd funding
python3 -m unittest -v
```

Tests use injected wallet/RPC functions with **no funds or real sessions**. They exercise duplicate/late inputs, exact amounts/caps, persistent interrupted dispatch, confirmed restart, plan binding and receipt mismatch. The hosted form has a separate backend test suite and isolated rehearsal campaign. Signed-out attendee access, the measured allowance, live RPC availability and one separately approved real transfer remain operational checks. Source tests and registration receipts do not establish a successful payout.
