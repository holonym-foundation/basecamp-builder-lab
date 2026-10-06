---
name: basecamp-sui-decision-lab
description: Explain and compare the Basecamp Sui Rebalancer and Liquidation Guardian workshop decision loops using the local workshop-agent.mjs helper.
---

Use this skill in an already configured coding agent with terminal access. It is a workshop lesson, not the full AEX runtime or a live trading service.

1. Ask the builder to choose Rebalancer or Guardian. Confirm the folder containing `workshop-agent.mjs` and Node 24. Do not install a wallet, request a private key or use any existing wallet session.
2. Inspect the helper source, then run exactly one chosen read/decision command:
   - `node workshop-agent.mjs rebalancer`
   - `node workshop-agent.mjs guardian --scenario at-risk`
3. Explain inputs, the resulting decision, and one limitation using the returned JSON. Rebalancer has a live Sui mainnet price and simulated holdings. Guardian uses simulated lending scenarios and a simplified single-debt model. Neither performs a transaction. Do not describe either output as a swap, repayment, deployed agent, live lending position, or guaranteed protection.
4. Ask for one change: allocation target or band for Rebalancer; scenario or target health factor for Guardian. Run the helper once again with that change. For example, `--target 0.7` for Rebalancer or `--scenario unknown` for Guardian. Compare outputs; do not alter the source to force success.
5. If a read fails, show the error and stop. Never invent prices, receipts, balances or a fresh health factor. Unknown lending data must remain a stop condition.
6. Save a short report with the selected recipe, settings, output, live/simulated boundary, and what the builder changed. Cite the pool/checkpoint from the actual output where available. Do not save private session data.
7. End after the two runs. No background schedule, paid service, signing, borrowing, swapping, repaying, or AEX deployment is part of this skill.

The chat model may have a cost under the builder's own existing account; the helper itself makes no model calls. The full public recipes and source catalogue are linked from https://holonym-foundation.github.io/basecamp-builder-lab/build.html#library.
