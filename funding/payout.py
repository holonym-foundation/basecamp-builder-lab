#!/usr/bin/env python3
"""Private Google Form export -> reviewed native SUI payouts. Python 3.11+, macOS/Linux."""
import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

NETWORKS = {
    'mainnet': ('https://sui-rpc.publicnode.com', '35834a8a'),
    'testnet': ('https://sui-testnet-rpc.publicnode.com', '4c78adac'),
}
U64 = 2**64 - 1


def require(ok, message):
    if not ok:
        raise ValueError(message)


def address(value):
    require(isinstance(value, str) and re.fullmatch(r'0x[0-9a-fA-F]{64}', value), 'Expected a full 32-byte Sui address')
    value = value.lower()
    require(int(value, 16) > 15, 'Reserved/system Sui address is not a recipient')
    return value


def email(value):
    require(isinstance(value, str), 'Expected participant email')
    value = value.strip().lower()
    require(len(value) <= 254 and re.fullmatch(r'[^\s@\x00-\x1f]+@[^\s@\x00-\x1f]+\.[^\s@\x00-\x1f]+', value), 'Invalid participant email')
    return value


def email_registration(row, start, end, sender):
    require(isinstance(row, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in row.items()), 'Malformed registration row')
    require(row.get('response_id'), 'Missing response ID')
    require(row.get('status') == 'selected', 'not-selected')
    require(row.get('binding_status') == 'participant-provided', 'Unsupported wallet binding status')
    when = timestamp(row['submitted_at'])
    require(start <= when < end, 'outside-window')
    participant = email(row['email'])
    recipient = address(row['address'].strip())
    require(recipient != sender, 'sender-is-recipient')
    return when, participant, recipient


def mist(value):
    require(isinstance(value, str) and re.fullmatch(r'(0|[1-9][0-9]*)(\.[0-9]{1,9})?', value), 'Use a positive SUI decimal with at most 9 places')
    whole, _, fraction = value.partition('.')
    amount = int(whole) * 10**9 + int((fraction + '0'*9)[:9])
    require(0 < amount <= U64, 'SUI amount out of range')
    return amount


def sui(value):
    return f'{value//10**9}.{value%10**9:09d}'.rstrip('0').rstrip('.')


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None, 'Timestamp must include timezone')
    return parsed


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_private(path, value):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open('xb') as file:
        os.chmod(path, 0o600)
        file.write(json.dumps(value, indent=2).encode() + b'\n')
        file.flush()
        os.fsync(file.fileno())


def make_plan(config, codes, rows, sender, amount, maximum, reserve):
    require(config['network'] in NETWORKS, 'Unsupported network')
    require(config['cap'] == 30, 'Campaign cap must be 30')
    start, end = timestamp(config['openedAt']), timestamp(config['closedAt'])
    require((end-start).total_seconds() == 900, 'Campaign must have a 15-minute window')
    require(dt.datetime.now(dt.timezone.utc) >= end, 'Registration has not closed')
    require(re.fullmatch(r'[a-zA-Z0-9-]{8,64}', config['campaign']), 'Invalid campaign ID')
    sender = address(sender)
    amount, maximum, reserve = mist(amount), mist(maximum), mist(reserve)
    if config.get('intake') == 'email':
        require(config.get('walletSource') == 'participant-provided' and config.get('requiresReview') is True,
                'Email campaign must declare participant-provided wallets requiring review')
        require(not codes, 'Invite codes do not apply to email intake')
        parsed, report, ids = [], [], set()
        for row in rows:
            rid = row.get('response_id', '')
            require(rid and rid not in ids, 'Missing/duplicate response ID; re-export the original form')
            ids.add(rid)
            try:
                if row.get('status') == 'waitlist':
                    report.append({'response_id': rid, 'status': 'waitlist'})
                    continue
                when, participant, recipient = email_registration(row, start, end, sender)
                parsed.append((when, rid, participant, recipient, dict(row)))
            except (ValueError, KeyError) as error:
                report.append({'response_id': rid, 'status': 'excluded', 'reason': str(error)})
        used_emails, used_wallets, recipients = set(), set(), []
        for when, rid, participant, recipient, row in sorted(parsed):
            if participant in used_emails or recipient in used_wallets:
                report.append({'response_id': rid, 'status': 'duplicate'})
                continue
            used_emails.add(participant)
            used_wallets.add(recipient)
            if len(recipients) >= 30:
                report.append({'response_id': rid, 'status': 'waitlist'})
                continue
            recipients.append({'address': recipient, 'email': participant, 'response_id': rid,
                               'registration': row, 'registrationHash': digest(row)})
            report.append({'response_id': rid, 'status': 'selected'})
        require(recipients, 'No eligible recipients')
        total = len(recipients)*amount
        require(total <= maximum <= U64, 'Recipient total exceeds the approved maximum')
        plan = dict(version=2, campaign=config['campaign'], network=config['network'], sender=sender,
                    intake='email', walletSource='participant-provided', requiresReview=True, cap=30,
                    openedAt=config['openedAt'], closedAt=config['closedAt'], amountMist=str(amount),
                    totalMist=str(total), maxTotalMist=str(maximum), gasReserveMist=str(reserve),
                    recipients=recipients)
        return {'plan': plan, 'sha256': digest(plan), 'report': report}
    require(config.get('intake') in (None, 'code'), 'Unsupported campaign intake')
    require(codes and len(codes) == len(set(codes)), 'Missing or duplicate private invite codes')
    require(all(re.fullmatch(r'[a-zA-Z0-9-]{8,64}', c) for c in codes), 'Invalid private invite code')
    valid_codes = set(codes)
    parsed, report = [], []
    ids = set()
    for row in rows:
        rid = row.get('response_id', '')
        require(rid and rid not in ids, 'Missing/duplicate response ID; re-export the original form')
        ids.add(rid)
        try:
            when = timestamp(row['submitted_at'])
            require(start <= when < end, 'outside-window')
            code = row['code'].strip()
            require(code in valid_codes, 'invalid-code')
            recipient = address(row['address'].strip())
            require(recipient != sender, 'sender-is-recipient')
            parsed.append((when, rid, code, recipient))
        except (ValueError, KeyError) as error:
            report.append({'response_id': rid, 'status': 'excluded', 'reason': str(error)})
    used_codes, used_wallets, recipients = set(), set(), []
    for when, rid, code, recipient in sorted(parsed):
        if code in used_codes or recipient in used_wallets:
            report.append({'response_id': rid, 'status': 'duplicate'})
            continue
        used_codes.add(code)
        used_wallets.add(recipient)
        if len(recipients) >= 30:
            report.append({'response_id': rid, 'status': 'waitlist'})
            continue
        recipients.append({'address': recipient, 'response_id': rid, 'codeHash': hashlib.sha256(code.encode()).hexdigest()})
        report.append({'response_id': rid, 'status': 'selected'})
    require(recipients, 'No eligible recipients')
    total = len(recipients)*amount
    require(total <= maximum <= U64, 'Recipient total exceeds the approved maximum')
    plan = dict(version=1, campaign=config['campaign'], network=config['network'], sender=sender,
                openedAt=config['openedAt'], closedAt=config['closedAt'], amountMist=str(amount),
                totalMist=str(total), maxTotalMist=str(maximum), gasReserveMist=str(reserve),
                recipients=recipients)
    return {'plan': plan, 'sha256': digest(plan), 'report': report}


def validate_plan(envelope):
    p = envelope['plan']
    require(envelope['sha256'] == digest(p), 'Plan hash mismatch')
    require(p['version'] in (1, 2) and p['network'] in NETWORKS, 'Unsupported plan')
    address(p['sender'])
    require(1 <= len(p['recipients']) <= 30, 'Invalid recipient count')
    recipients = [address(r['address']) for r in p['recipients']]
    require(len(recipients) == len(set(recipients)) and p['sender'] not in recipients, 'Duplicate/self recipient')
    if p['version'] == 1:
        require(len({r['codeHash'] for r in p['recipients']}) == len(recipients), 'Duplicate invite')
    else:
        require(p.get('intake') == 'email' and p.get('walletSource') == 'participant-provided'
                and p.get('requiresReview') is True and p.get('cap') == 30, 'Invalid email plan review requirements')
        seen_emails, seen_ids = set(), set()
        for recipient in p['recipients']:
            row = recipient['registration']
            require(recipient['registrationHash'] == digest(row), 'Registration hash mismatch')
            _, participant, wallet = email_registration(row, timestamp(p['openedAt']), timestamp(p['closedAt']), p['sender'])
            require(recipient['email'] == participant and recipient['address'] == wallet
                    and recipient['response_id'] == row['response_id'], 'Recipient differs from registration')
            require(participant not in seen_emails and row['response_id'] not in seen_ids, 'Duplicate email/registration')
            seen_emails.add(participant)
            seen_ids.add(row['response_id'])
    amount, total, maximum, reserve = (int(p[k]) for k in ('amountMist', 'totalMist', 'maxTotalMist', 'gasReserveMist'))
    require(0 < amount <= total <= maximum <= U64 and total == len(recipients)*amount and 0 < reserve <= U64, 'Invalid totals')
    require((timestamp(p['closedAt'])-timestamp(p['openedAt'])).total_seconds() == 900, 'Invalid window')
    require(dt.datetime.now(dt.timezone.utc) >= timestamp(p['closedAt']), 'Registration not closed')
    return p


def result_event(text):
    events = [json.loads(line) for line in text.splitlines() if line.strip()]
    require(all(isinstance(e, dict) and e.get('event') != 'error' for e in events), 'CLI error; inspect before proceeding')
    results = [e for e in events if e.get('event') == 'result']
    require(len(results) == 1, 'Missing or ambiguous CLI result')
    return results[0]


def waap(executable, *args):
    # No shell, passwords or private keys. Operator supplies an isolated, logged-in CLI session.
    run = subprocess.run([executable, *args, '--json'], capture_output=True, text=True, timeout=180)
    require(run.returncode == 0, 'CLI failed; payout outcome may be unknown. Do not resend.')
    return result_event(run.stdout)


def rpc(network, method, params):
    endpoint, _ = NETWORKS[network]
    data = canonical({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    # curl uses the host's TLS/proxy configuration; URLs are fixed, no shell or redirects.
    response = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--max-time', '20',
                               endpoint, '-H', 'Content-Type: application/json', '--data-binary', '@-'],
                              input=data, capture_output=True, timeout=25)
    require(response.returncode == 0, 'RPC request failed; stop and reconcile')
    result = json.loads(response.stdout)
    require('error' not in result and 'result' in result, 'RPC unavailable or rejected request; stop and reconcile')
    return result['result']


def verify_receipt(plan, recipient, tx_digest, rpc_fn=rpc):
    require(re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', tx_digest), 'Invalid transaction digest')
    receipt = rpc_fn(plan['network'], 'sui_getTransactionBlock', [tx_digest, {'showInput': True, 'showEffects': True, 'showBalanceChanges': True}])
    require(receipt.get('digest') == tx_digest, 'Wrong receipt digest')
    require(receipt.get('effects', {}).get('status', {}).get('status') == 'success', 'Transaction not confirmed successful')
    require(receipt.get('transaction', {}).get('data', {}).get('sender') == plan['sender'], 'Wrong receipt sender')
    require(receipt.get('checkpoint') is not None, 'Receipt is not checkpointed yet; reconcile later')
    changes = receipt.get('balanceChanges', [])
    received = sum(int(c['amount']) for c in changes if c.get('owner', {}).get('AddressOwner', '').lower() == recipient and c.get('coinType') == '0x2::sui::SUI')
    require(received == int(plan['amountMist']), 'Receipt does not prove the exact recipient allowance')
    # Reject an older payment being used to resolve a new dispatch.
    return receipt


def open_ledger(path):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = open(str(path)+'.lock', 'a')
    os.chmod(str(path)+'.lock', 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    db = sqlite3.connect(path)
    os.chmod(path, 0o600)
    db.execute('PRAGMA synchronous=EXTRA')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, plan_hash TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS payments (
        campaign TEXT NOT NULL, address TEXT NOT NULL, status TEXT NOT NULL,
        started_ms INTEGER NOT NULL, digest TEXT UNIQUE, receipt TEXT,
        PRIMARY KEY(campaign,address));
    ''')
    return db, lock


def bind_plan(db, envelope):
    plan = validate_plan(envelope)
    with db:
        db.execute('INSERT OR IGNORE INTO campaigns VALUES (?,?)', (plan['campaign'], envelope['sha256']))
        recorded = db.execute('SELECT plan_hash FROM campaigns WHERE id=?', (plan['campaign'],)).fetchone()[0]
        require(recorded == envelope['sha256'], 'Campaign already bound to a different plan; do not create a new ledger to bypass it')
    return plan


def complete(db, p, wallet, tx, rpc_fn=rpc):
    state = db.execute('SELECT status,started_ms,digest FROM payments WHERE campaign=? AND address=?', (p['campaign'], wallet)).fetchone()
    require(state is not None, 'No persisted dispatch to reconcile')
    require(state[2] in (None, tx), 'Cannot replace a recorded digest')
    receipt = verify_receipt(p, wallet, tx, rpc_fn)
    require(int(receipt.get('timestampMs', 0)) >= state[1], 'Receipt predates this dispatch')
    with db:
        db.execute('UPDATE payments SET status=?,digest=?,receipt=? WHERE campaign=? AND address=?', ('confirmed', tx, json.dumps(receipt), p['campaign'], wallet))


def execute(db, envelope, executable, send=waap, rpc_fn=rpc):
    p = bind_plan(db, envelope)
    require(os.environ.get('WAAP_CLI_SESSION_DIR'), 'Set an isolated WAAP_CLI_SESSION_DIR; do not use a rehearsal session')
    require(rpc_fn(p['network'], 'sui_getChainIdentifier', []) == NETWORKS[p['network']][1], 'RPC network identity mismatch')
    who = send(executable, 'whoami')
    require(address(who.get('suiWalletAddress')) == p['sender'], 'Logged-in wallet differs from reviewed sender')
    unresolved = db.execute("SELECT address FROM payments WHERE campaign=? AND status!='confirmed'", (p['campaign'],)).fetchall()
    require(not unresolved, 'Unresolved payout exists. Reconcile it; execution will not resend.')
    for item in p['recipients']:
        wallet = item['address']
        if db.execute('SELECT 1 FROM payments WHERE campaign=? AND address=?', (p['campaign'], wallet)).fetchone():
            continue
        balance = int(rpc_fn(p['network'], 'suix_getBalance', [p['sender'], '0x2::sui::SUI'])['totalBalance'])
        count = db.execute("SELECT count(*) FROM payments WHERE campaign=? AND status='confirmed'", (p['campaign'],)).fetchone()[0]
        require(balance >= (len(p['recipients'])-count)*int(p['amountMist'])+int(p['gasReserveMist']), 'Insufficient sender balance including approved gas reserve')
        with db: # Commit durable intent BEFORE invoking any sending command.
            db.execute('INSERT INTO payments VALUES (?,?,?,?,NULL,NULL)', (p['campaign'], wallet, 'dispatching', int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)))
        result = send(executable, 'send-tx', '--chain', 'sui:'+p['network'], '--to', wallet, '--value', sui(int(p['amountMist'])), '--wait')
        tx = result.get('txHash') or result.get('digest')
        require(isinstance(tx, str) and re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', tx), 'Unknown submission result. Preserve ledger; do not resend.')
        require(not result.get('txHash') or not result.get('digest') or result['txHash'] == result['digest'], 'Conflicting receipt digests')
        with db:
            db.execute('UPDATE payments SET digest=? WHERE campaign=? AND address=?', (tx, p['campaign'], wallet))
        complete(db, p, wallet, tx, rpc_fn)
        print(f'Confirmed {wallet}: https://suiscan.xyz/{p["network"]}/tx/{tx}', flush=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    plan = sub.add_parser('plan')
    for name in ('campaign', 'csv', 'sender', 'amount-sui', 'max-total-sui', 'gas-reserve-sui', 'out'):
        plan.add_argument('--'+name, required=True)
    plan.add_argument('--codes', help='Private invite-code CSV; required only for legacy code campaigns')
    for name in ('execute', 'reconcile', 'report'):
        command = sub.add_parser(name)
        command.add_argument('--plan', required=True)
        command.add_argument('--ledger', required=True)
        if name == 'execute':
            command.add_argument('--confirm', required=True, help='Exact SHA256 shown by plan')
            command.add_argument('--waap', required=True, help='Absolute path to installed waap-cli 2.2.1 executable')
        elif name == 'reconcile':
            command.add_argument('--address', required=True)
            command.add_argument('--digest', required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        codes = []
        if args.codes:
            with open(args.codes, newline='') as file:
                codes = [r['code'].strip() for r in csv.DictReader(file)]
        with open(args.csv, newline='', encoding='utf-8-sig') as file:
            rows = list(csv.DictReader(file))
        envelope = make_plan(json.loads(Path(args.campaign).read_text()), codes, rows, args.sender, args.amount_sui, args.max_total_sui, args.gas_reserve_sui)
        write_private(args.out, envelope)
        p = envelope['plan']
        if p.get('intake') == 'email':
            print('Participant-provided email/wallet pairs are not ownership-verified. Review every pair before approving this plan hash.')
        print(f'{len(p["recipients"])} recipients on {p["network"]}; {sui(int(p["amountMist"]))} SUI each; total {sui(int(p["totalMist"]))} SUI, plus gas.\nSender: {p["sender"]}\nReview every recipient in {args.out}\nConfirmation hash: {envelope["sha256"]}\nNO FUNDS SENT.')
        return
    envelope = json.loads(Path(args.plan).read_text())
    p = validate_plan(envelope)
    if args.command == 'execute':
        require(args.confirm == envelope['sha256'], 'Exact reviewed plan hash required')
        require(Path(args.waap).is_absolute() and Path(args.waap).is_file(), 'Provide the absolute waap-cli executable path')
        version = subprocess.run([args.waap, '--version'], capture_output=True, text=True, timeout=15)
        require(version.returncode == 0 and version.stdout.strip() == '2.2.1', 'Expected waap-cli 2.2.1')
    db, lock = open_ledger(args.ledger)
    try:
        p = bind_plan(db, envelope)
        if args.command == 'execute':
            execute(db, envelope, args.waap)
        elif args.command == 'reconcile':
            require(rpc(p['network'], 'sui_getChainIdentifier', []) == NETWORKS[p['network']][1], 'RPC network mismatch')
            complete(db, p, address(args.address), args.digest)
            print('Receipt verified. No transaction sent.')
        else:
            records = db.execute('SELECT address,status,digest FROM payments WHERE campaign=?', (p['campaign'],)).fetchall()
            print(json.dumps({'campaign': p['campaign'], 'payments': [dict(zip(('address','status','digest'), r)) for r in records]}, indent=2))
    finally:
        db.close()
        lock.close()


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(f'STOPPED: {error}', file=sys.stderr)
        sys.exit(1)
