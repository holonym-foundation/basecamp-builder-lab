# AEX · Sui Basecamp Builder Lab

Public workshop materials for **Trade. Guard. Hunt. Claim. Build Agents That Do It All.**

- [Audience deck](https://holonym-foundation.github.io/basecamp-builder-lab/deck/)
- [Presenter companion](https://holonym-foundation.github.io/basecamp-builder-lab/deck/presenter.html)
- [Rebalancer build guide](https://holonym-foundation.github.io/basecamp-builder-lab/deploy.html)
- [Funding registration](https://holonym-foundation.github.io/basecamp-builder-lab/register.html)
- [Public recipe library](https://holonym-foundation.github.io/basecamp-builder-lab/build.html#library)

The site root redirects to the build guide. The earlier Pool Watcher page has been removed from the workshop.

## Workshop sequence

1. Slide 15: download the Rebalancer kit and launch its local console with Node 24.
2. Slide 16: create or sign in to a wallet, save its Sui address and configure the strategy. No balance is required yet.
3. Slide 17: register the wallet email and saved address for workshop funds.
4. Slide 18: install dependencies, run the recipe and inspect the decision.
5. Change a rule, compare results and stop monitoring.

The local Rebalancer reads actual mainnet prices and wallet balances. It proposes SUI/USDC swaps using price thresholds and a SUI dollar target. The distributed kit builds and simulates unsigned transactions; signing and submission are not enabled. HOLD, BUY SUI or SELL SUI is distinct from execution status.

## Funding

The public form requires no ChatGPT login. The first 30 unique email/address pairs are selected; later pairs join the waitlist. The optional 15-minute reminder does not gate submissions. The host can explicitly close intake.

Operator controls export registrations. A separate local payout script prepares a reviewed plan and sends only when invoked with its exact confirmation hash. The form does not send funds. See [funding/README.md](funding/README.md) and the companion's funding walkthrough. Keep operator keys, sessions, exports and payout ledgers private.

## Additional recipes

`build.html#library` links the public Sui recipe guides, Cetus phases, DeepBook source, reusable agent skills and other WaaP recipes. The browser Rebalancer and Guardian exercises on that page are older decision-only lessons: sample holdings or labelled scenarios, with no signing. They are separate from the standalone Rebalancer kit.

`hunt.html` is the non-chain research exercise. `cli.html` is a separate Sui testnet wallet quickstart.

## Maintaining the materials

`scripts/update-builder-deck.py` regenerates both HTML deck variants and the companion. `scripts/build-presenter-companion.py` owns the companion's timing and instructions. These scripts do not regenerate older venue PDF/PPTX files.

`node --test builders/workshop-agent.test.mjs` checks the browser lesson logic. `python3 -m unittest discover -s funding` checks offline payout planning and injected execution cases; those tests do not send real funds.
