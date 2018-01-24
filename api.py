# coding: utf-8

import json
import datetime
import hashlib
import webapp2

from google.appengine.api import users, memcache
from google.appengine.ext import ndb

import sil_model
import split_pgn

CHUNK_SIZE = 10
"""
Make sample opening PGN
parse_stm verkar inte klara kommentarer (med åäö?)

--- LATER ---
Memorize games:
 find worthy games
 maybe import from chessgames.com?
 choose source type
 if source is "game", choose moves
 "forgive me"-knapp som säger att draget inte ska räknas som fel

Instant assessment:
 Autogenerate such FENs + score from DB
 Way to input and score assessment

Semi-blind tactics:
 find games with tactic (crawl or calculate, preferably crawl)
 Show position X moves before
 Promote to other than queen

Make design nicer with semantic UI instead of jquery ui

More fact management:
 keep fact times for same ID
 inaktivera fact
 list facts for source (so can reactivate)
 delete facts when source deleted

Ta bort omedelbar stat, efter create
Create-spinner
Custom CSS for mobile
Fix open new window, board bug
"""


def add_success(fact):
    memdb = memcache.Client()
    i = memdb.incr('nranswer_%s' % fact.userid, initial_value=0)
    return i


def add_fail(fact):
    memdb = memcache.Client()
    i = memdb.incr('nranswer_%s' % fact.userid, initial_value=0)
    fails = memdb.get(fact.userid)
    if not fails:
        fails = []
    fails = [f for f in fails if f != fact]
    fails.append((fact, i - 1))
    fails = fails[-CHUNK_SIZE:]
    memdb.set(fact.userid, fails)


def get_fail(user_id):
    memdb = memcache.Client()
    fails = memdb.get(user_id)
    if not fails:
        return None
    i = memdb.get('nranswer_%s' % user_id)
    if i is None:
        i = 0
    if fails[0][1] + CHUNK_SIZE > i:
        return None
    fact = fails.pop(0)[0]
    memdb.set(user_id, fails)
    return fact


def get_fact(source_id, fact_id):
    fact = ndb.Key(sil_model.Factlet,
                   long(fact_id),
                   parent=ndb.Key(sil_model.Source, long(source_id))).get()
    return fact


class RestHandler(webapp2.RequestHandler):
    def jsonify(self, d):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(d))


class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write('Hello, World!')


class CreateSource(RestHandler):
    def get(self):
        user = users.get_current_user()
        query = sil_model.Source.query(
            sil_model.Source.userid == user.user_id())

        self.jsonify(
            {'sources': [source.to_jdict() for source in query.iter()]})

    def post(self):
        user = users.get_current_user()
        source = sil_model.Source(
            userid=user.user_id(),
            name=self.request.get('name'),
            fact_type=self.request.get('fact_type'))
        source.put()

        self.jsonify({'key': source.key.id()})


class SingleSource(RestHandler):
    def get(self, source_id):
        source = ndb.Key(sil_model.Source, long(source_id)).get()

        d = source.to_jdict()
        d['facts'] = [f.to_jdict()
                      for f in sil_model.Factlet.query_source(source_id)]
        self.jsonify(d)

    def delete(self, source_id):
        ndb.Key(sil_model.Source, long(source_id)).delete()


class CreateFact(RestHandler):
    def get(self):
        user = users.get_current_user()
        query = sil_model.Factlet.query(
            sil_model.Factlet.userid == user.user_id())

        self.jsonify(
            {'keys': [key.id() for key in query.iter(keys_only=True)]})

    def post(self):
        user = users.get_current_user()
        fact = self.request.get('fact').encode('utf8')

        fact_obj = sil_model.Factlet(
            parent=ndb.Key(sil_model.Source,
                           long(self.request.get('source_id'))),
            userid=user.user_id(),
            fact=fact, )
        fact_obj.put()

        self.jsonify({'key': fact_obj.key.id()})


class SingleFact(RestHandler):
    def get(self, source_id, fact_id):
        fact = get_fact(source_id, fact_id)

        self.jsonify(fact.to_jdict())

    def delete(self, source_id, fact_id):
        parent = ndb.Key(sil_model.Source, long(source_id))
        ndb.Key(sil_model.Factlet, long(fact_id), parent=parent).delete()


class SourceLearner(RestHandler):
    def get(self, source_id):
        user = users.get_current_user()
        fact = get_fail(user.user_id())

        if not fact or int(fact.key.parent().get().key.id()) != int(source_id):
            fact = sil_model.Factlet.get_next(user.user_id(), source_id)

        self.jsonify(fact.to_jdict())


class Answer(SourceLearner):
    def post(self, source_id, fact_id, result):
        fact = get_fact(source_id, fact_id)
        if result == 'success':
            fact.success()
            add_success(fact)
        else:
            fact.fail()
            add_fail(fact)
        fact.put()

        self.get(source_id)


class SourceStat(RestHandler):
    def get(self, source_id):
        user = users.get_current_user()
        tot = sil_model.Factlet.count(user.user_id(), source_id)
        left = sil_model.Factlet.count_left(user.user_id(), source_id)

        nextfact = sil_model.Factlet.get_next(user.user_id(), source_id)
        if nextfact:
            next = (nextfact.next_scheduled - datetime.datetime(1970, 1, 1)
                    ).total_seconds()
        else:
            next = 0
        self.jsonify({'total': tot,
                      'left': left,
                      'key': source_id,
                      'next': next})


class AddOpening(RestHandler):
    def post(self, source_id):
        user = users.get_current_user()
        source = ndb.Key(sil_model.Source, long(source_id))
        color = self.request.get('color')

        def make_fact(pgn, headers):
            hid = hashlib.md5(user.user_id() + ''.join(x['move'] for x in
                                                       pgn)).hexdigest()
            hid = int(hid[:14], 16)
            fd = {'moves': pgn, 'orientation': color}
            if 'FEN' in headers:
                fd['fen'] = headers['FEN']
                fd['orientation'] = 'b' if ' w ' in fd['fen'] else 'w'
            fact = sil_model.Factlet(
                parent=source,
                id=hid,
                userid=user.user_id(),
                # use 'fen' for start positions
                fact=json.dumps(fd), )
            return fact

        pgns = split_pgn.split_pgns(self.request.get('pgn'), color == 'w')
        keys = ndb.put_multi(
            [make_fact(pgn, headers) for pgn, headers in pgns])

        self.jsonify({'keys': [key.id() for key in keys]})


class StageData(RestHandler):
    def get(self):
        user = users.get_current_user()

        source = sil_model.Source(
            userid=user.user_id(), name='stage', fact_type='opening')
        source.put()

        color = 'b'

        def make_fact(pgn):
            fact = sil_model.Factlet(
                parent=source.key,
                userid=user.user_id(),
                # use 'fen' for start positions
                fact=json.dumps({'moves': pgn,
                                 'orientation': color}), )
            return fact

        pgns = split_pgn.split_pgn(open('data/black.pgn').read(), color == 'w')
        keys = ndb.put_multi([make_fact(pgn) for pgn in pgns])

        self.jsonify(source.key.id())


app = webapp2.WSGIApplication(
    [
        ('/', MainPage), ('/fact', CreateFact), ('/source', CreateSource),
        ('/source/(\d+)', SingleSource), ('/source/(\d+)/(\d+)', SingleFact),
        ('/source/(\d+)/(\d+)/(success|fail)',
         Answer), ('/source/(\d+)/next', SourceLearner),
        ('/source/(\d+)/stat', SourceStat),
        ('/source/(\d+)/opening', AddOpening), ('/stagedata', StageData)
    ],
    debug=True)
