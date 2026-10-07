// Basecamp teaching loops: no wallet, signing, paid inference or transaction submission.
// Run in Node 24, or import the same functions from build.html.
export const POOL = '0xb8d7d9e66a60c239e7a60110efcf8de6c705580ed924d0dde141f4a0e2c90105';
const USDC = '0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC';
const SUI = '0x0000000000000000000000000000000000000000000000000000000000000002::sui::SUI';
function finite(value, name, min = 0) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min) throw Error(`Invalid ${name}`);
  return value;
}
export async function readPrice({onEvent = () => {}} = {}) {
  onEvent({operation:"Sui GraphQL request", detail:"POST graphql.mainnet.sui.io/graphql · pool object + checkpoint"});
  const query = `{ object(address: "${POOL}") { asMoveObject { contents { json type { repr } } } } checkpoint { sequenceNumber timestamp } }`;
  const res = await fetch('https://graphql.mainnet.sui.io/graphql', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query}), signal: AbortSignal.timeout(15000),
  });
  if (!res.ok) throw Error(`Sui read failed: HTTP ${res.status}`);
  const response = await res.json();
  onEvent({operation:"Sui GraphQL response", detail:`HTTP ${res.status} · validating pair, pause state and checkpoint freshness`});
  if (response.errors) throw Error(response.errors[0].message);
  const {object, checkpoint} = response.data;
  const contents = object?.asMoveObject?.contents;
  if (!contents?.type.repr.endsWith(`<${USDC},${SUI}>`)) throw Error('Unexpected pool pair');
  if (contents.json.is_pause) throw Error('Pool paused');
  const age = Date.now() - Date.parse(checkpoint?.timestamp);
  if (!Number.isFinite(age) || age > 120000 || age < -30000) throw Error('Chain timestamp stale or local clock incorrect');
  // Coin A = USDC (6 decimals), B = SUI (9). Q64.64 gives B/A.
  const ratio = Number(BigInt(contents.json.current_sqrt_price)) / 2 ** 64;
  const price = 1 / (ratio * ratio * 10 ** (6 - 9));
  finite(price, 'price', Number.MIN_VALUE);
  onEvent({operation:"Pool read verified", detail:`Checkpoint ${checkpoint.sequenceNumber} · SUI $${price.toFixed(6)} · ${checkpoint.timestamp}`});
  return {price, chain: 'Sui mainnet', checkpoint: checkpoint.sequenceNumber,
    chainTime: checkpoint.timestamp, readAt: new Date().toISOString(),
    pool: POOL, explorer: `https://suiscan.xyz/mainnet/object/${POOL}`};
}
export function rebalance(price, target = .5, band = .05) {
  finite(price, 'price', Number.MIN_VALUE); finite(target, 'target'); finite(band, 'band');
  if (target > 1 || band > 1) throw Error('Target and band must be between 0 and 1');
  // Fictional holdings for comparing decisions. No wallet balance is read.
  const sampleSui = 10, sampleUsdc = 10;
  const total = sampleSui * price + sampleUsdc;
  const allocation = sampleSui * price / total;
  const deltaUsdc = target * total - sampleSui * price;
  return {holdings: 'SIMULATED: 10 SUI + 10 USDC', target, band,
    currentAllocation: allocation,
    decision: Math.abs(allocation - target) <= band ? 'HOLD' : deltaUsdc > 0 ? 'PROPOSE_BUY_SUI' : 'PROPOSE_SELL_SUI',
    proposedValueUsdc: Math.abs(allocation - target) <= band ? 0 : Math.abs(deltaUsdc),
    execution: 'NONE — decision only; fees, route and slippage not modelled'};
}
export function guardian(scenario = 'at-risk', target = 1.3) {
  finite(target, 'target health factor', 1.01);
  const scenarios = {
    healthy: {liquidationCapacityUsd: 150, weightedDebtUsd: 100},
    'at-risk': {liquidationCapacityUsd: 110, weightedDebtUsd: 100},
    'no-debt': {liquidationCapacityUsd: 110, weightedDebtUsd: 0},
    unknown: {liquidationCapacityUsd: null, weightedDebtUsd: 100},
  };
  if (!Object.hasOwn(scenarios, scenario)) throw Error('Use healthy, at-risk, no-debt or unknown');
  const p = scenarios[scenario];
  // Teaching model: single $1 debt asset with 1x borrow weight. Not a protocol quote.
  const base = {source: 'SIMULATED lending scenario', scenario, ...p, target,
    perActionCapUsd: 10, execution: 'NONE — no lending position is opened or changed'};
  if (p.liquidationCapacityUsd === null) return {...base, decision: 'STOP_UNKNOWN_DATA'};
  if (p.weightedDebtUsd === 0) return {...base, decision: 'NO_DEBT', healthFactor: null};
  const healthFactor = p.liquidationCapacityUsd / p.weightedDebtUsd;
  const needed = Math.max(0, p.weightedDebtUsd - p.liquidationCapacityUsd / target);
  const proposedRepayUsd = Math.min(10, needed);
  return {...base, healthFactor, decision: needed > 0 ? 'PROPOSE_REPAY' : 'OBSERVE',
    neededRepayUsd: needed, proposedRepayUsd,
    targetRestoredWithinCap: needed <= 10,
    explanation: needed > 10 ? 'Cap is insufficient to restore target; request human review.' : 'Check fresh protocol data before considering any action.'};
}
export async function run(recipe, options = {}) {
  if (recipe === 'rebalancer') {
    const live = await readPrice(options);
    options.onEvent?.({operation:"rebalance()", detail:`Calculating target ${100 * (options.target ?? .5)}% · sample holdings 10 SUI + 10 USDC`});
    return {recipe: 'Sui Rebalancer workshop loop', ...live,
      ...rebalance(live.price, options.target ?? .5, options.band ?? .05)};
  }
  if (recipe === 'guardian') options.onEvent?.({operation:"guardian()", detail:`Calculating labelled ${options.scenario ?? 'at-risk'} scenario · target ${options.target ?? 1.3} · no network request`});
  if (recipe === 'guardian') return {recipe: 'Liquidation Guardian workshop loop',
    ...guardian(options.scenario ?? 'at-risk', options.target ?? 1.3)};
  throw Error('Choose rebalancer or guardian');
}
if (typeof process !== 'undefined' && process.versions?.node && process.argv[1]?.endsWith('workshop-agent.mjs')) {
  const [recipe, ...args] = process.argv.slice(2);
  const options = {};
  try {
    for (let i = 0; i < args.length; i += 2) {
      const key = args[i].replace(/^--/, '');
      if (!['target', 'band', 'scenario'].includes(key) || !args[i + 1]) throw Error('Use --target, --band or --scenario followed by a value');
      options[key] = key === 'scenario' ? args[i + 1] : Number(args[i + 1]);
    }
    console.log(JSON.stringify(await run(recipe, options), null, 2));
  } catch (error) { console.error(`Stopped: ${error.message}`); process.exitCode = 1; }
}
