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


if __name__ == '__main__':
    unittest.main()
