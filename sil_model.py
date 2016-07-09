import datetime

from google.appengine.ext import ndb

START_SKIP = 60
LEARN_FACTOR = 5
MAX_MINUTES = 60 * 24 * 365 * 2


def fix_datetime(d):
    for k in d:
        if isinstance(d[k], datetime.datetime):
            d[k] = d[k].isoformat()
    return d


class JsonModel(ndb.Model):

    def to_jdict(self):
        d = self.to_dict()
        fix_datetime(d)
        d['key'] = str(self.key.id())
        return d


class Source(JsonModel):
    userid = ndb.StringProperty(required=True)
    name = ndb.TextProperty()
    fact_type = ndb.StringProperty()


class Factlet(JsonModel):
    userid = ndb.StringProperty(required=True)
    fact = ndb.BlobProperty(required=True)
    added = ndb.DateTimeProperty(auto_now_add=True)
    last_seen = ndb.DateTimeProperty(auto_now_add=True)
    next_scheduled = ndb.DateTimeProperty(auto_now_add=True)
    cur_increase = ndb.IntegerProperty(default=START_SKIP)  # minutes
    trials = ndb.IntegerProperty(default=0)
    fails = ndb.IntegerProperty(default=0)

    def fail(self):
        now = datetime.datetime.now()
        self.trials += 1
        self.fails += 1
        self.cur_increase = START_SKIP
        self.next_scheduled = now
        self.last_seen = now

    def success(self):
        now = datetime.datetime.utcnow()
        self.trials += 1
        interval = (now - self.last_seen).total_seconds() / 60

        self.cur_increase = int(min(
            max(self.cur_increase, interval * LEARN_FACTOR), MAX_MINUTES))
        self.next_scheduled = now + \
            datetime.timedelta(0, self.cur_increase * 60)
        self.last_seen = now

    @classmethod
    def get_fact_query(cls, userid, source_id=None):
        if source_id is not None:
            q = cls.query(cls.userid == userid, ancestor=ndb.Key(
                Source, long(source_id)))
        else:
            q = cls.query(userid=userid)
        return q

    @classmethod
    def count(cls, userid, source_id=None):
        q = cls.get_fact_query(userid, source_id)
        return q.count(10000)

    @classmethod
    def count_left(cls, userid, source_id=None):
        now = datetime.datetime.now()
        q = cls.get_fact_query(userid, source_id)
        q = q.filter(cls.next_scheduled <= now)
        cnt = q.count(1000)
        return cnt

    @classmethod
    def get_next(cls, userid, source_id=None):
        q = cls.get_fact_query(userid, source_id)
        return q.order(cls.next_scheduled).get()

    @classmethod
    def query_source(cls, source_id):
        return cls.query(ancestor=ndb.Key(Source, long(source_id))).order(cls.added)
