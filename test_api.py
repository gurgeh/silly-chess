import unittest
import datetime
import json
import sys

sys.path.insert(1, '/home/gurgeh/Downloads/google_appengine/')
sys.path.insert(1, '/home/gurgeh/Downloads/google_appengine/lib')

from google.appengine.ext import testbed
from google.appengine.ext import ndb

import api


class TestJson(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Next, declare which service stubs you want to use.
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        # Clear ndb's in-context cache between tests.
        # This prevents data from leaking between tests.
        # Alternatively, you could disable caching by
        # using ndb.get_context().set_cache_policy(False)
        ndb.get_context().clear_cache()

        self.testbed.setup_env(
            user_email='user@example.com',
            user_id='123',
            user_is_admin='0',
            overwrite=True)

    def tearDown(self):
        self.testbed.deactivate()

    def create_sources(self, n):
        keys = []
        for i in range(n):
            d = self.ask(
                '/source', POST={'name': 'n%d' % i, 'fact_type': 'f%d' % i})
            keys.append(d['key'])
        return keys

    def create_facts(self, source_id, n):
        keys = []
        for i in range(n):
            d = self.ask(
                '/fact', POST={'source_id': source_id, 'fact': 'f%s' % i})
            keys.append(d['key'])

        return keys

    def ask(self, *args, **kwargs):
        response = api.app.get_response(*args, **kwargs)
        self.assertEqual(response.status_int, 200)
        try:
            return json.loads(response.body)
        except ValueError:
            return None


class TestCRUD(TestJson):

    def test_create_source(self):
        d = self.ask('/source')
        self.assertEqual(d['keys'], [])

        keys = self.create_sources(15)

        d = self.ask('/source')
        self.assertEqual(len(d['keys']), 15)
        self.assertEqual(set(d['keys']), set(keys))

        d = self.ask('/source/%s' % keys[1])
        self.assertEqual(d['name'], 'n1')
        self.assertEqual(d['fact_type'], 'f1')

    def test_delete_source(self):
        keys = self.create_sources(2)

        d = self.ask('/source')
        self.assertEqual(len(d['keys']), 2)

        d = self.ask('/source/%s' % keys[0], method='DELETE')

        d = self.ask('/source')
        self.assertEqual(d['keys'], [keys[1]])

    def test_create_fact(self):
        skeys = self.create_sources(2)

        d = self.ask('/fact')
        self.assertEqual(d['keys'], [])

        fkey = self.ask(
            '/fact', POST={'source_id': skeys[1], 'fact': 'fact0'})['key']

        d = self.ask('/fact')
        self.assertEqual(d['keys'], [fkey])

        d2 = self.ask('/source/%s' % skeys[1])
        self.assertEqual(d['keys'], [x['key'] for x in d2['facts']])

        d = self.ask('/source/%s' % skeys[0])
        self.assertEqual(d['facts'], [])

    def test_delete_fact(self):
        skeys = self.create_sources(1)
        fkey0 = self.ask(
            '/fact', POST={'source_id': skeys[0], 'fact': 'fact0'})['key']
        d = self.ask('/fact')
        self.assertEqual(d['keys'], [fkey0])

        fkey1 = self.ask(
            '/fact', POST={'source_id': skeys[0], 'fact': 'fact1'})['key']

        d = self.ask('/source/%s/%s' % (skeys[0], fkey0), method='DELETE')

        d = self.ask('/source/%s' % skeys[0])
        self.assertEqual([x['key'] for x in d['facts']], [fkey1])


class TestSIL(TestJson):
    NRSOURCES = 2
    NRFACTS = 100

    def get_started(self):
        skeys = self.create_sources(self.NRSOURCES)
        self.create_facts(skeys[1], self.NRFACTS)

        seen = set()
        q = self.ask('/source/%s/next' % skeys[1])
        seen.add(q['key'])

        return q, skeys, seen

    def test_fail(self):
        q, skeys, seen = self.get_started()

        for i in xrange(api.CHUNK_SIZE - 1):
            q = self.ask('/source/%s/%s/fail' %
                         (skeys[1], q['key']), method='POST')
            self.assertNotIn(q['key'], seen)  # New questions
            seen.add(q['key'])

        for i in xrange(api.CHUNK_SIZE):
            q = self.ask('/source/%s/%s/fail' %
                         (skeys[1], q['key']), method='POST')
            self.assertIn(q['key'], seen)  # Cached question
            seen.remove(q['key'])

    def test_success(self):
        q, skeys, seen = self.get_started()

        for i in xrange(self.NRFACTS - 1):
            q = self.ask('/source/%s/%s/success' %
                         (skeys[1], q['key']), method='POST')
            self.assertNotIn(q['key'], seen)  # New questions
            seen.add(q['key'])

        q = self.ask('/source/%s/%s/success' %
                     (skeys[1], q['key']), method='POST')
        self.assertIn(q['key'], seen)  # Back again

        self.assertEqual(int(round((datetime.datetime.strptime(q['next_scheduled'], "%Y-%m-%dT%H:%M:%S.%f") -
                                    datetime.datetime.utcnow()).total_seconds() / 60)), api.sil_model.START_SKIP)
        seen = set()
        seen.add(q['key'])
        for i in xrange(self.NRFACTS - 1):
            q = self.ask('/source/%s/%s/success' %
                         (skeys[1], q['key']), method='POST')
            self.assertNotIn(q['key'], seen)  # New questions
            seen.add(q['key'])

        q = self.ask('/source/%s/%s/success' %
                     (skeys[1], q['key']), method='POST')
        self.assertIn(q['key'], seen)  # Back again

        self.assertEqual(int(round((datetime.datetime.strptime(q['next_scheduled'], "%Y-%m-%dT%H:%M:%S.%f") -
                                    datetime.datetime.utcnow()).total_seconds() / 60)), api.sil_model.START_SKIP)

    def test_mixed(self):
        q, skeys, seen = self.get_started()

        q = self.ask('/source/%s/%s/fail' %
                     (skeys[1], q['key']), method='POST')
        seen.add(q['key'])

        for i in xrange(api.CHUNK_SIZE - 2):
            q = self.ask('/source/%s/%s/success' %
                         (skeys[1], q['key']), method='POST')
            self.assertNotIn(q['key'], seen)  # New questions
            seen.add(q['key'])

        q = self.ask('/source/%s/%s/fail' %
                     (skeys[1], q['key']), method='POST')
        self.assertIn(q['key'], seen)  # Cached question


class TestPGN(TestJson):

    def test_split(self):
        skey = self.create_sources(1)[0]
        with open('data/test.pgn') as f:
            d = self.ask('/source/%s/opening' %
                         skey, POST={'pgn': f.read(), 'color': 'b'})

        self.assertEqual(len(d['keys']), 3)

        d = self.ask('/fact')

        self.assertEqual(len(d['keys']), 3)


if __name__ == '__main__':
    unittest.main()
