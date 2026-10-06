# Workshop funding: 15-minute form → private CSV → local payouts

This fallback does not require AEX. It collects **individual workshop codes and Sui addresses** in a Google Form, selects at most **30 valid unique registrations**, and uses the operator's WaaP CLI to send a measured allowance. Everyone else is waitlisted. No allowance is built into this kit.

The public QR opens the form, not a wallet, payment request or claim link. The form always says submission received, not funds sent or place guaranteed. Individual invite codes are distributed privately, one per person. Duplicate codes/addresses cannot get another allocation. This does not identify humans: someone with multiple legitimately issued codes and wallets could submit multiple times; staff controls code issuance.

## 1. Prepare the private form

In your Google account, create a project at https://script.google.com, paste `Form.gs`, and run `setupFundingForm`. Approve the Google Forms/Drive permissions. It creates a **closed** form and a private Drive folder containing 60 individual codes. Do not share that folder, the code list or response exports publicly. Use the logged participant URL to generate the QR (never the form edit URL). Test respondent access signed out; your Workspace administrator may restrict external forms.

The setup runs once. If setup fails halfway, preserve its existing form/folder IDs and repair the setup; do not clear properties and unknowingly create another active campaign.

Make a QR locally (no form responses are sent to a third-party QR service):

```sh
python3 -m venv /tmp/basecamp-qr-env
/tmp/basecamp-qr-env/bin/pip install 'qrcode[pil]==8.2'
/tmp/basecamp-qr-env/bin/python funding/qr.py --url 'YOUR_PUBLISHED_FORM_URL' --out /tmp/registration-qr.png
```

Show the QR and run `openFundingWindow` in Apps Script when ready. The window is **15 minutes**, cannot be reopened by rerunning the function, and the cutoff is saved in `campaign.json`. The closing trigger can be delayed by Google: **the payout planner enforces the exact cutoff**, regardless of when the form visually closes. Form submissions remain requests; the planner selects the first 30 eligible unique responses by server timestamp (response ID breaks exact ties). Entries beyond 30 become a private waitlist.

This is not AEX's server-enforced account admission. It is a capped payout selection after a form closes; it never promises a seat before validation.

## 2. Export and review

After the window ends, run `exportFundingResponses`. Download its CSV, `codes.csv` and `campaign.json` into a private local folder. Use this helper's CSV, not Google's locale-dependent default export. Do not edit timestamps, IDs or the window after collection. An existing plan remains bound to its campaign in the ledger.

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

Tests use injected wallet/RPC functions with **no funds or real sessions**. They exercise duplicate/late inputs, exact amounts/caps, persistent interrupted dispatch, confirmed restart, plan binding and receipt mismatch. A Google-account form setup, signed-out submission, actual export, live RPC check and one separately approved real transfer remain operator rehearsal steps. Source tests do not establish those live results.
