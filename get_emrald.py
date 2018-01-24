import re
import random
import pickle

import progressbar
import requests

URL = "http://chess.emrald.net/psolution.php?Pos="


def get_pos(i):
    h = requests.get(URL + str(i))
    try:
        xs = re.findall("text/javascript'>([^<]+)<", h.text)
    except Exception as e:
        print('Error %s (%d)' % (e, i))
        return
    if len(xs) != 3:
        print("%d len %d" % (i, len(xs)))
    else:
        return xs[0]


def get_all_pos(start, end):
    bar = progressbar.ProgressBar()
    nrs = list(range(start, end))
    random.shuffle(nrs)
    rets = []
    for i in bar(nrs):
        ret = get_pos(i)
        if ret:
            rets.append((i, ret))

    try:
        with open('emrald.p', 'wb') as outf:
            pickle.dump(rets, outf)
    except Exception as e:
        print(e)
    return rets
