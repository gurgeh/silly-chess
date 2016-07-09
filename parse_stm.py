#!/usr/bin/env python2.7
# coding: utf-8

import re
import sys

import chess.pgn

import parse_stm2

MOVE_REX_S = "{([^ ]+) [^ ]+ \w+ (?:{([^}]*)}|([^ ]+)) [^ ]+ [^ ]+}"

POSITION_REX = re.compile(
    "{([\w\d/]+ [wb] [KkQq\-]+ .\d?)}")
STM_REX = re.compile(
    "{([\w\d/]+ [wb] [KkQq\-]+ .\d?)} {{((?:" + MOVE_REX_S + " ?)*)} {}}", re.U)
MOVE_REX = re.compile(
    MOVE_REX_S, re.U)

"""
def parse_stm(s):
    i = s.find('{')
    s = s[i:]
    s = s.replace('\\}', ']')
    s = s.replace('\\{', '[')
    s = s.replace('\ ', '\t')
    open('/tmp/test.stm', 'w').write(s.encode('utf8'))
    return STM_REX.finditer(s)


def missing(s):
    allpos = set(POSITION_REX.findall(s))
    stmpos = set(x[0] for x in parse_stm(s))
    return allpos - stmpos


def get_moves(s):
    for m, c1, c2 in MOVE_REX.findall(s):
        comment = c1 + c2
        if m == 'null':
            continue
        yield m, comment


def postodict(positions):
    return {'%s 0 1' % m.group(1): list(get_moves(m.group(2))) for m in positions}
"""


def get_node(posd, node):
    fen = node.board().fen()
    bulk, _, _ = fen.rsplit(' ', 2)
    return posd.get('%s 0 1' % bulk, [])


def to_game(posd):
    g = chess.pgn.Game()

    def rec_add(node):
        moves = get_node(posd, node)
        trunk = 0
        leaf = 0
        if moves:
            trunk = 1
        else:
            leaf = 1
        for move, comment in moves:
            try:
                newmove = node.board().parse_san(move)
            except ValueError, e:
                print node.board().fen(), move, comment, e
            newnode = node.add_variation(newmove)
            newnode.comment = comment
            ntrunk, nleaf = rec_add(newnode)
            trunk += ntrunk
            leaf += nleaf
        return trunk, leaf

    print rec_add(g)
    return g

if __name__ == '__main__':
    inname = sys.argv[1]
    outname = '%s.pgn' % inname.rsplit('.', 1)[0]

    with open(inname) as inf:
        g = to_game(parse_stm2.postodict(parse_stm2.parseSTM(inf)))
        with open(outname, 'w') as outf:
            s = unicode(g)
            outf.write(s.encode('utf8'))
