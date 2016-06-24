# coding: utf-8

import json

import webapp2

from google.appengine.api import users, memcache
from google.appengine.ext import ndb

import sil_model
import split_pgn

CHUNK_SIZE = 10
"""
enkelt interface
 Ladda upp testpgn med
  olika orientation
  flera okmoves
  kommentarer
  promovering
  rockad
  passant
  flera icke-ask moves i rad
-
 Översiktsida
  + Create New Source (name)
  - Delete Source (are you sure?)
  - Upload PGN (choose file, choose side)
  - Show source statistics
  - Click to train

 Board statistics

--- LATER ---
Memorize games:
 upload games with masks for which moves are good
 paste PGN, incl start-FEN
 maybe import from chessgames.com?
 "forgive me"-knapp som säger att draget inte ska räknas som fel
 Promote to other than queen

Instant assessment:
 Autogenerate such FENs + score from DB
 Way to input and score assessment

Semi-blind tactics:
 find games with tactic (crawl or calculate, preferably crawl)
 Show position X moves before

More fact management:
 update facts (comments)
 reload PGN and update
 inaktivera fact
 list facts for source (so can reactivate)

Custom CSS for mobile
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
    fact = ndb.Key(sil_model.Factlet, long(fact_id),
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
            {'keys': [key.id() for key in query.iter(keys_only=True)]})

    def post(self):
        user = users.get_current_user()
        source = sil_model.Source(userid=user.user_id(),
                                  name=self.request.get('name'),
                                  fact_type=self.request.get('fact_type'))
        source.put()

        self.jsonify({'key': source.key.id()})


class SingleSource(RestHandler):

    def get(self, source_id):
        source = ndb.Key(sil_model.Source, long(source_id)).get()

        d = source.to_dict()
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

        fact = sil_model.Factlet(
            parent=ndb.Key(sil_model.Source, long(
                self.request.get('source_id'))),
            userid=user.user_id(),
            fact=self.request.get('fact').encode('utf8'),
        )
        fact.put()

        self.jsonify({'key': fact.key.id()})


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
        if not fact:
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

        self.jsonify({'total': tot, 'left': left})


class AddOpening(RestHandler):

    def post(self, source_id):
        user = users.get_current_user()
        source = ndb.Key(sil_model.Source, long(source_id))
        color = self.request.get('color')

        def make_fact(pgn):
            fact = sil_model.Factlet(
                parent=source,
                userid=user.user_id(),
                # use 'fen' for start positions
                fact=json.dumps({'moves': pgn, 'orientation': color}),
            )
            return fact

        pgns = split_pgn.split_pgn(self.request.get('pgn'), color == 'w')
        keys = ndb.put_multi([make_fact(pgn) for pgn in pgns])

        self.jsonify({'keys': [key.id() for key in keys]})


class StageData(RestHandler):

    def get(self):
        user = users.get_current_user()

        source = sil_model.Source(userid=user.user_id(),
                                  name='stage',
                                  fact_type='opening')
        source.put()

        color = 'b'

        def make_fact(pgn):
            fact = sil_model.Factlet(
                parent=source.key,
                userid=user.user_id(),
                # use 'fen' for start positions
                fact=json.dumps({'moves': pgn, 'orientation': color}),
            )
            return fact

        pgns = split_pgn.split_pgn(open('data/black.pgn').read(), color == 'w')
        keys = ndb.put_multi([make_fact(pgn) for pgn in pgns])

        self.jsonify(source.key.id())


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/fact', CreateFact),
    ('/source', CreateSource),
    ('/source/(\d+)', SingleSource),
    ('/source/(\d+)/(\d+)', SingleFact),
    ('/source/(\d+)/(\d+)/(success|fail)', Answer),
    ('/source/(\d+)/next', SourceLearner),
    ('/source/(\d+)/stat', SourceStat),
    ('/source/(\d+)/opening', AddOpening),
    ('/stagedata', StageData)


], debug=True)
