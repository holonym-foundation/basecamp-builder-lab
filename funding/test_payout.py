import copy
import datetime as dt
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import payout as p


def wallet(n):
    return '0x' + f'{n+100:064x}'


class PayoutTests(unittest.TestCase):
    def setUp(self):
        self.config = {'campaign': 'workshop-test-campaign', 'network': 'testnet', 'cap': 30,
                       'openedAt': '2026-01-01T04:30:00Z', 'closedAt': '2026-01-01T04:45:00Z'}
        self.codes = [f'private-code-{n:03}' for n in range(60)]

    def rows(self, count=1):
        return [{'response_id': f'response-{n:03}', 'submitted_at': '2026-01-01T04:31:00Z',
                 'code': self.codes[n], 'address': wallet(n)} for n in range(count)]

    def plan(self, rows=None):
        return p.make_plan(self.config, self.codes, rows or self.rows(), wallet(999), '0.000000001', '1', '0.1')

    def test_exact_mist_arithmetic(self):
        self.assertEqual(p.mist('0.000000001'), 1)
        self.assertEqual(p.mist('123.456789123'), 123456789123)
        for bad in ('0', '-1', '1e3', '1.0000000001', 'NaN', ' 1', '18446744074'):
            with self.assertRaises(ValueError): p.mist(bad)

    def test_cap_waitlist_and_sort(self):
        result = self.plan(list(reversed(self.rows(60))))
        self.assertEqual(len(result['plan']['recipients']), 30)
        self.assertEqual(result['plan']['recipients'][0]['response_id'], 'response-000')
        self.assertEqual(sum(r['status']=='waitlist' for r in result['report']), 30)

    def test_duplicates_invalid_and_cutoff(self):
        rows = self.rows(7)
        rows[1]['address'] = rows[0]['address'].upper().replace('0X', '0x')
        rows[2]['code'] = rows[0]['code']
        rows[3]['submitted_at'] = self.config['closedAt']
        rows[4]['code'] = 'unknown-code'
        rows[5]['address'] = '0x1234'
        rows[6]['address'] = wallet(999)
        result = self.plan(rows)
        self.assertEqual(len(result['plan']['recipients']), 1)
        self.assertEqual(sum(r['status']=='duplicate' for r in result['report']), 2)

    def test_budget_future_window_and_mutation_refused(self):
        with self.assertRaises(ValueError):
            p.make_plan(self.config, self.codes, self.rows(2), wallet(999), '1', '1', '0.1')
        config = dict(self.config, openedAt='2099-01-01T04:30:00Z', closedAt='2099-01-01T04:45:00Z')
        with self.assertRaises(ValueError):
            p.make_plan(config, self.codes, self.rows(), wallet(999), '1', '1', '0.1')
        result = self.plan()
        result['plan']['amountMist'] = '100'
        with self.assertRaises(ValueError): p.validate_plan(result)

    def test_csv_reexport_cannot_repeat_response_ids(self):
        with self.assertRaises(ValueError): self.plan(self.rows()+self.rows())

    def test_receipt_must_prove_sender_amount_success_checkpoint(self):
        plan = self.plan()['plan']
        receipt = self.receipt(plan, wallet(0))
        p.verify_receipt(plan, wallet(0), 'a'*44, lambda *_: receipt)
        for changed in ({'checkpoint': None}, {'transaction': {'data': {'sender': wallet(1)}}},
                        {'effects': {'status': {'status': 'failure'}}}, {'balanceChanges': []}):
            with self.assertRaises(ValueError):
                p.verify_receipt(plan, wallet(0), 'a'*44, lambda *_: dict(receipt, **changed))

    def receipt(self, plan, recipient):
        return {'digest': 'a'*44, 'checkpoint': '123',
                'timestampMs': str(int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)+100),
                'transaction': {'data': {'sender': plan['sender']}}, 'effects': {'status': {'status': 'success'}},
                'balanceChanges': [{'owner': {'AddressOwner': recipient}, 'coinType': '0x2::sui::SUI', 'amount': plan['amountMist']}]}

    def fake_rpc(self, plan):
        def call(network, method, params):
            if method == 'sui_getChainIdentifier': return p.NETWORKS[network][1]
            if method == 'suix_getBalance': return {'totalBalance': str(10**12)}
            return self.receipt(plan, wallet(0))
        return call

    @patch.dict(os.environ, {'WAAP_CLI_SESSION_DIR': '/synthetic-test-session'})
    def test_interrupted_dispatch_is_never_retried(self):
        envelope = self.plan()
        sent = []
        def fake_send(exe, *args):
            if args[0] == 'whoami': return {'suiWalletAddress': wallet(999)}
            sent.append(args)
            raise TimeoutError('injected lost response')
        with tempfile.TemporaryDirectory() as directory:
            db, lock = p.open_ledger(Path(directory)/'ledger.sqlite')
            try:
                with self.assertRaises(TimeoutError): p.execute(db, envelope, '/fake', fake_send, self.fake_rpc(envelope['plan']))
                with self.assertRaisesRegex(ValueError, 'Unresolved'):
                    p.execute(db, envelope, '/fake', fake_send, self.fake_rpc(envelope['plan']))
                self.assertEqual(len(sent), 1)
                p.complete(db, envelope['plan'], wallet(0), 'a'*44, self.fake_rpc(envelope['plan']))
                p.execute(db, envelope, '/fake', fake_send, self.fake_rpc(envelope['plan']))
                self.assertEqual(len(sent), 1)
            finally:
                db.close(); lock.close()

    @patch.dict(os.environ, {'WAAP_CLI_SESSION_DIR': '/synthetic-test-session'})
    def test_confirmed_restart_no_double_pay_and_plan_binding(self):
        envelope = self.plan()
        sent = []
        def fake_send(exe, *args):
            if args[0] == 'whoami': return {'suiWalletAddress': wallet(999)}
            sent.append(args)
            return {'txHash': 'a'*44}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ledger.sqlite'
            db, lock = p.open_ledger(path)
            p.execute(db, envelope, '/fake', fake_send, self.fake_rpc(envelope['plan']))
            db.close(); lock.close()
            db, lock = p.open_ledger(path)
            try:
                p.execute(db, envelope, '/fake', fake_send, self.fake_rpc(envelope['plan']))
                self.assertEqual(len(sent), 1)
                changed = copy.deepcopy(envelope)
                changed['plan']['gasReserveMist'] = '2'
                changed['sha256'] = p.digest(changed['plan'])
                with self.assertRaisesRegex(ValueError, 'different plan'): p.bind_plan(db, changed)
            finally:
                db.close(); lock.close()

    def test_old_receipt_and_concurrent_executor_refused(self):
        envelope = self.plan()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'ledger.sqlite'
            db, lock = p.open_ledger(path)
            try:
                with self.assertRaises(BlockingIOError): p.open_ledger(path)
                with db:
                    db.execute('INSERT INTO payments VALUES (?,?,?,?,NULL,NULL)', (envelope['plan']['campaign'], wallet(0), 'dispatching', 9999999999999))
                with self.assertRaisesRegex(ValueError, 'predates'): p.complete(db, envelope['plan'], wallet(0), 'a'*44, self.fake_rpc(envelope['plan']))
            finally:
                db.close(); lock.close()

    def test_cli_result_rejects_errors_and_ambiguity(self):
        self.assertEqual(p.result_event('{"event":"result","txHash":"abc"}')['txHash'], 'abc')
        for bad in ('{}', '{"event":"error"}', '{"event":"result"}\n{"event":"result"}'):
            with self.assertRaises(ValueError): p.result_event(bad)

    @patch.dict(os.environ, {'WAAP_CLI_SESSION_DIR': '/synthetic-test-session'})
    def test_preflight_failures_never_dispatch(self):
        envelope = self.plan()
        for failure in ('network', 'sender', 'balance'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                db, lock = p.open_ledger(Path(directory)/'ledger.sqlite')
                sent = []
                def fake_send(exe, *args):
                    if args[0] == 'whoami':
                        return {'suiWalletAddress': wallet(1 if failure == 'sender' else 999)}
                    sent.append(args)
                def fake_rpc(network, method, params):
                    if method == 'sui_getChainIdentifier':
                        return 'wrong-network' if failure == 'network' else p.NETWORKS[network][1]
                    return {'totalBalance': '0'}
                try:
                    with self.assertRaises(ValueError): p.execute(db, envelope, '/fake', fake_send, fake_rpc)
                    self.assertEqual(sent, [])
                    self.assertEqual(db.execute('SELECT count(*) FROM payments').fetchone()[0], 0)
                finally:
                    db.close(); lock.close()


class EmailPayoutTests(unittest.TestCase):
    def setUp(self):
        self.config = {'campaign': 'basecamp-email-20261007', 'network': 'testnet', 'cap': 30,
                       'openedAt': '2026-01-01T04:30:00Z', 'closedAt': '2026-01-01T04:45:00Z',
                       'intake': 'email', 'walletSource': 'participant-provided', 'requiresReview': True}

    def rows(self, count=1):
        return [{'response_id': f'{n:04}-registration', 'submitted_at': '2026-01-01T04:31:00Z',
                 'email': f'builder+{n}@example.test', 'address': wallet(n),
                 'status': 'selected', 'binding_status': 'participant-provided'} for n in range(count)]

    def plan(self, rows=None, config=None):
        return p.make_plan(config or self.config, [], rows if rows is not None else self.rows(), wallet(999), '0.1', '3', '0.1')

    def test_no_codes_and_full_registration_binding(self):
        rows = self.rows()
        rows[0]['email'] = ' Builder+0@Example.Test '
        rows[0]['address'] = rows[0]['address'].upper().replace('0X', '0x')
        rows[0]['extra_evidence'] = 'retain every exported field'
        result = self.plan(rows)
        plan = p.validate_plan(result)
        self.assertEqual(plan['version'], 2)
        self.assertEqual(plan['recipients'][0]['email'], 'builder+0@example.test')
        self.assertEqual(plan['recipients'][0]['registration'], rows[0])
        self.assertNotIn('codeHash', plan['recipients'][0])
        for key in rows[0]:
            changed = copy.deepcopy(result)
            changed['plan']['recipients'][0]['registration'][key] += 'changed'
            changed['sha256'] = p.digest(changed['plan'])
            with self.assertRaisesRegex(ValueError, 'Registration hash'): p.validate_plan(changed)

    def test_normalized_email_wallet_dedupe_and_plus_preservation(self):
        rows = self.rows(5)
        rows[1]['email'] = ' BUILDER+0@EXAMPLE.TEST '
        rows[2]['address'] = rows[0]['address'].upper().replace('0X', '0x')
        result = self.plan(rows)
        self.assertEqual(len(result['plan']['recipients']), 3)
        self.assertEqual(sum(r['status'] == 'duplicate' for r in result['report']), 2)
        self.assertEqual([r['email'] for r in result['plan']['recipients']],
                         ['builder+0@example.test', 'builder+3@example.test', 'builder+4@example.test'])

    def test_server_waitlist_never_promoted_and_cap_enforced(self):
        rows = self.rows(33)
        rows[0]['status'] = 'waitlist'
        result = self.plan(list(reversed(rows)))
        self.assertEqual(len(result['plan']['recipients']), 30)
        self.assertNotIn(rows[0]['response_id'], [r['response_id'] for r in result['plan']['recipients']])
        self.assertEqual(sum(r['status'] == 'waitlist' for r in result['report']), 3)
        with self.assertRaises(ValueError): self.plan([rows[0]])

    def test_late_malformed_unknown_binding_and_nonselected_excluded(self):
        rows = self.rows(7)
        rows[1]['submitted_at'] = self.config['closedAt']
        rows[2]['email'] = 'not an email'
        rows[3]['binding_status'] = 'verified'
        rows[4]['status'] = 'candidate'
        rows[5]['address'] = wallet(999)
        del rows[6]['email']
        result = self.plan(rows)
        self.assertEqual(len(result['plan']['recipients']), 1)
        self.assertEqual(sum(r['status'] == 'excluded' for r in result['report']), 6)
        with self.assertRaises(ValueError): self.plan(self.rows()+self.rows())

    def test_campaign_review_window_capacity_required(self):
        for change in ({'requiresReview': False}, {'walletSource': 'verified'}, {'cap': 31},
                       {'closedAt': '2026-01-01T04:46:00Z'}, {'intake': 'unexpected'},
                       {'openedAt': '2099-01-01T04:30:00Z', 'closedAt': '2099-01-01T04:45:00Z'}):
            with self.subTest(change=change), self.assertRaises(ValueError): self.plan(config=dict(self.config, **change))
        with self.assertRaises(ValueError):
            p.make_plan(self.config, ['unused-code'], self.rows(), wallet(999), '0.1', '3', '0.1')

    def test_rehashed_plan_cannot_substitute_recipient_or_promote_waitlist(self):
        original = self.plan()
        for field, value in [('email', 'another@example.test'), ('address', wallet(2)), ('response_id', 'replacement')]:
            changed = copy.deepcopy(original)
            changed['plan']['recipients'][0][field] = value
            changed['sha256'] = p.digest(changed['plan'])
            with self.assertRaisesRegex(ValueError, 'differs from registration'): p.validate_plan(changed)
        changed = copy.deepcopy(original)
        r = changed['plan']['recipients'][0]
        r['registration']['status'] = 'waitlist'
        r['registrationHash'] = p.digest(r['registration'])
        changed['sha256'] = p.digest(changed['plan'])
        with self.assertRaisesRegex(ValueError, 'not-selected'): p.validate_plan(changed)

    def test_cli_plan_without_codes_is_private_and_never_sends(self):
        import csv
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'campaign.json').write_text(json.dumps(self.config))
            with (root/'registrations.csv').open('w', newline='') as output:
                writer = csv.DictWriter(output, fieldnames=list(self.rows()[0]))
                writer.writeheader(); writer.writerows(self.rows())
            result = subprocess.run([sys.executable, str(Path(p.__file__)), 'plan',
                '--campaign', str(root/'campaign.json'), '--csv', str(root/'registrations.csv'),
                '--sender', wallet(999), '--amount-sui', '0.1', '--max-total-sui', '3',
                '--gas-reserve-sui', '0.1', '--out', str(root/'plan.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('NO FUNDS SENT', result.stdout)
            self.assertIn('not ownership-verified', result.stdout)
            self.assertEqual((root/'plan.json').stat().st_mode & 0o777, 0o600)
            p.validate_plan(json.loads((root/'plan.json').read_text()))

    def test_email_plan_uses_existing_no_retry_and_receipt_execution(self):
        # Reuse the existing executor fault/receipt scenarios with a v2 plan.
        legacy = PayoutTests()
        legacy.setUp()
        legacy.plan = self.plan
        legacy.test_interrupted_dispatch_is_never_retried()
        legacy.test_confirmed_restart_no_double_pay_and_plan_binding()


class AdvisoryPayoutTests(unittest.TestCase):
    setUp = EmailPayoutTests.setUp
    rows = EmailPayoutTests.rows
    plan = EmailPayoutTests.plan
    def advisory(self, rows=None, **changes):
        config = dict(self.config, version=2, windowPolicy='advisory', selectionPolicy='first-come-first-served', openedAt=None, closedAt=None)
        config.update(changes)
        if rows is None:
            rows = self.advisory_rows()
        return self.plan(rows, config=config)

    def advisory_rows(self, count=1):
        rows = self.rows(count)
        for n, row in enumerate(rows, 1):
            row['response_id'] = f'{n:04}-registration'
            row['status'] = 'selected' if n <= 30 else 'waitlist'
        return rows

    def test_advisory_accepts_no_timer_before_open_and_after_expiry(self):
        for timer in ({}, {'openedAt': '2099-01-01T04:30:00Z', 'closedAt': '2099-01-01T04:45:00Z'},
                      {'openedAt': '2020-01-01T04:30:00Z', 'closedAt': '2020-01-01T04:45:00Z'}):
            with self.subTest(timer=timer):
                result = self.advisory(**timer)
                self.assertEqual(p.validate_plan(result)['version'], 3)
        config = dict(self.config, version=2, windowPolicy='advisory', selectionPolicy='first-come-first-served')
        del config['openedAt']; del config['closedAt']
        p.validate_plan(self.plan(self.advisory_rows(), config))

    def test_rank_beats_timestamps_and_preserves_first_thirty(self):
        rows = self.advisory_rows(44)
        rows[0]['submitted_at'] = '2026-02-01T00:00:00Z'
        result = self.advisory(list(reversed(rows)))
        plan = p.validate_plan(result)
        self.assertEqual(len(plan['recipients']), 30)
        self.assertEqual(len(plan['registrationRows']), 44)
        self.assertEqual(plan['recipients'][0]['response_id'], '0001-registration')
        self.assertEqual(plan['recipients'][-1]['response_id'], '0030-registration')
        self.assertEqual(sum(row['status']=='waitlist' for row in result['report']), 14)

    def test_export_gaps_duplicates_and_status_conflicts_rejected(self):
        for kind in ('gap', 'duplicate-rank', 'duplicate-email', 'duplicate-wallet', 'early-waitlist', 'late-selected'):
            with self.subTest(kind=kind):
                rows = self.advisory_rows(31)
                if kind == 'gap': rows.pop(0)
                elif kind == 'duplicate-rank': rows[1]['response_id'] = '0001-another'
                elif kind == 'duplicate-email': rows[1]['email'] = ' BUILDER+0@EXAMPLE.TEST '
                elif kind == 'duplicate-wallet': rows[1]['address'] = rows[0]['address']
                elif kind == 'early-waitlist': rows[0]['status'] = 'waitlist'
                elif kind == 'late-selected': rows[-1]['status'] = 'selected'
                with self.assertRaises(ValueError): self.advisory(rows)

    def test_advisory_plan_cannot_reorder_or_drop_recipients(self):
        result = self.advisory(self.advisory_rows(3))
        for mutate in ('reverse', 'drop', 'row-field'):
            changed = copy.deepcopy(result)
            if mutate == 'reverse': changed['plan']['recipients'].reverse()
            elif mutate == 'drop': changed['plan']['recipients'].pop(0)
            else: changed['plan']['registrationRows'][0]['email'] = 'replacement@example.test'
            changed['sha256'] = p.digest(changed['plan'])
            with self.assertRaises(ValueError): p.validate_plan(changed)
        for key, value in [('version', 3), ('windowPolicy', 'ignored'), ('selectionPolicy', 'random')]:
            with self.assertRaises(ValueError): self.advisory(**{key: value})

    def test_advisory_execution_preserves_no_retry_and_receipt_binding(self):
        legacy = PayoutTests(); legacy.setUp(); legacy.plan = self.advisory
        legacy.test_interrupted_dispatch_is_never_retried()
        legacy.test_confirmed_restart_no_double_pay_and_plan_binding()


if __name__ == '__main__':
    unittest.main()
