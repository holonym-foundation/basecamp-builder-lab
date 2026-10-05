# Basecamp Builder Lab: Guard and Hunt

A single web page for the Sui Basecamp Builder Lab. It watches the Cetus USDC/SUI pool on Sui mainnet and simulates where a concentrated-liquidity position would sit. It is the monitor phase of the WaaP [Cetus Yield Agent recipe](https://docs.waap.human.tech/recipes), running in the browser.

- Reads one public pool object from `graphql.mainnet.sui.io`.
- No wallet, no keys, no transactions, no backend.
- Same output lines as the terminal version of the recipe.
- Shows the latest real transactions on the pool and the most recent real position opened on it, each linked to Suiscan.
- **Check a transaction**: paste any Sui digest (or use `?tx=<digest>`) to see its status, sender, balance changes and gas, read live from chain.

## Use it

Open the page and press **Start**. Workshop edit: change **Range** from 200 to 400, press **Reset**, then **Start**, and compare the `SIMULATED RANGE` lines.

URL presets: `?range=400&autostart=1` starts with the edit applied; `?threshold=5` makes a rebalance easy to trigger.

## Hunt card

`hunt.html` is the non-chain workshop exercise: one research prompt for any chat agent with browsing, plus steps to check every link it returns.
