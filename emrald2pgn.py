import pickle
import re

import chess
import chess.pgn

KEYVALREX = re.compile("\s([^=]+)\s*=\s*([^;]+)")


def trans(m):
    row = (63 - m) // 8
    col = m % 8
    return row * 8 + col


def parse_em(em):
    d = {'board': [], 'act_source': [], 'act_target': []}
    for key, val in KEYVALREX.findall(em):
        if key.startswith('Boards'):
            d['board'].append(eval(val))
        if key.startswith('ActFrom'):
            d['act_source'].append(int(eval(val)))
        if key.startswith('ActTo'):
            d['act_target'].append(int(eval(val)))

    if not d['board']:
        return None, 0

    fen = ems2fen(d['board'][0])
    b = chess.Board(fen)

    for src, target in zip(d['act_source'], d['act_target']):
        b.push(chess.Move(trans(src), trans(target)))

    return str(chess.pgn.Game.from_board(b)), len(d['act_source'])


def ems2fen(ems):
    b, color = ems.split()
    fen = '/'.join([b[i:i + 8] for i in range(0, len(b), 8)])
    for n in range(8, 0, -1):
        fen = fen.replace('x' * n, str(n))
    return fen + ' ' + color + ' KQkq - 0 1'


def save_pgns(pgnd):
    def chunks(l, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(l), n):
            yield l[i:i + n]

    for key in pgnd:
        for i, games in enumerate(chunks(pgnd[key], 200)):
            with open('tactics/%d_%d.pgn' % (key / 2, i), 'wt') as outf:
                for game in games:
                    outf.write(game)
                    outf.write('\n\n')
