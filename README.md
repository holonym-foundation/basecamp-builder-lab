# Basecamp Builder Lab: Rebalancer and Guardian

A single web page for the Sui Basecamp Builder Lab. It watches the Cetus USDC/SUI pool on Sui mainnet and simulates where a concentrated-liquidity position would sit. It is the monitor phase of the WaaP [Cetus Yield Agent recipe](https://docs.waap.human.tech/recipes), running in the browser.

- Reads one public pool object from `graphql.mainnet.sui.io`.
- No wallet, no keys, no transactions, no backend.
- Same output lines as the terminal version of the recipe.
- Shows the latest real transactions on the pool and the most recent real position opened on it, each linked to Suiscan.
- **Check a transaction**: paste any Sui digest (or use `?tx=<digest>`; add `&net=testnet` for testnet) to see its status, sender, balance changes and gas, read live from chain.

## Use it

Open the page and press **Start**. Workshop edit: change **Range** from 200 to 400, press **Reset**, then **Start**, and compare the `SIMULATED RANGE` lines.

URL presets: `?range=400&autostart=1` starts with the edit applied; `?threshold=5` makes a rebalance easy to trigger.

## Hunt card

`hunt.html` is the non-chain workshop exercise: one research prompt for any chat agent with browsing, plus steps to check every link it returns.

## Agent wallet quickstart

`cli.html` walks a builder through the WaaP CLI on Sui testnet: create an agent wallet, check its policy, fund it from the faucet, send a transaction and verify it on chain. Every step was tested with waap-cli 2.2.1.


## Follow along with a starter

Open [build.html](https://holonym-foundation.github.io/basecamp-builder-lab/build.html). It links the two lead workshop loops, the public starter skills, the hosted catalogue and the wider docs recipes.

- **Rebalancer:** public live Sui pool price + simulated holdings; proposes an allocation change.
- **Guardian:** labelled lending scenarios + capped protective proposal; no live position or repayment.
- Download `builders/workshop-agent.mjs` and run with Node 24. No dependencies, wallet or backend. The browser uses the same module.
- `builders/SKILL.md` adds an optional explain/change/compare flow for a builder's already configured coding agent.
- The full Guardian starter is not in the checked public agent-exchange repository. Do not describe this lesson as that deployment.

Run `node --test builders/workshop-agent.test.mjs` to check decisions and failure cases.

## Deck and presenter guide

The two v4 HTML entry points use the same participant route. `deck/presenter.html` has the exact screen switches, commands and timing. `scripts/update-builder-deck.py` updates both variants and regenerates the presenter guide from their slide cues. QR assets are local. This update does not regenerate the older venue PDF/PPTX.


## Workshop registration

The attendee form is [register.html](https://holonym-foundation.github.io/basecamp-builder-lab/register.html), on the same GitHub Pages site as the deck. No ChatGPT sign-in or wallet connection is required. The deck's build slides offer a **Build QR / Funding QR** toggle.

GitHub Pages hosts the form; the public registration backend stores submissions and enforces the 15-minute window, first 30 places, waitlist and duplicate rules. Only the Pages origin and the backend's own origin may submit through browsers. Operator controls and exports require the separate private key; it is never part of this repository.

The operator opens the real window only after announcing the measured allowance and confirming wallet/network instructions. Public hosting does not open registration or send funds. See the funding fallback PR for the export and local payout runbook.


## Present without typing commands

The programme title stays **Trade. Guard. Hunt. Claim. Build Agents That Do It All.**

- At minute 20 show **Build QR**: everyone opens the builder guide.
- Around minute 21, optionally open the funding window and briefly show **Funding QR**; return to Build QR. Registration runs in parallel and is not a prerequisite for the lessons.
- At minutes 23–34 click **Run Rebalancer** or **Run Guardian** inside the deck. The embedded five-step walkthrough executes the same browser helper as the downloadable source: baseline, change, compare, inspect evidence, save. Lead one recipe with the room following along.
- At minute 34 return to **Now make it yours**. Participants work independently until minute 51, then share their results.

The embedded demo uses `build.html?present=1#rebalancer` or `#guardian`. Run buttons execute in the browser; they do not execute a shell on the presenter's laptop. Local terminal commands remain optional. The presenter companion has the detailed cues.
