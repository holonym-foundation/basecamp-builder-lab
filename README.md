# Guard: read-only Sui pool watcher

A single web page for the Sui Basecamp Builder Lab. It watches the Cetus USDC/SUI pool on Sui mainnet and simulates where a concentrated-liquidity position would sit. It is the monitor phase of the WaaP [Cetus Yield Agent recipe](https://docs.waap.human.tech/recipes), running in the browser.

- Reads one public pool object from `graphql.mainnet.sui.io`.
- No wallet, no keys, no transactions, no backend.
- Same output lines as the terminal version of the recipe.

## Use it

Open the page and press **Start**. Workshop edit: change **Range** from 200 to 400, press **Reset**, then **Start**, and compare the `SIMULATED RANGE` lines.

URL presets: `?range=400&autostart=1` starts with the edit applied; `?threshold=5` makes a rebalance easy to trigger.
