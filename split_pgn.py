import StringIO

import chess.pgn


class Splitter(chess.pgn.BaseVisitor):

    def __init__(self, turn):
        chess.pgn.BaseVisitor.__init__(self)
        self.games = set()
        self.turn = turn

    def end_variation(self):
        if self.board.turn == self.turn:
            self.board.push(self.move)
        g = chess.pgn.Game.from_board(self.board)
        self.games.add(str(g))

    def end_game(self):
        self.end_variation()

    def visit_move(self, board, move):
        self.board = board.copy()
        self.move = move


def split_pgns(s, turn):
    lines = []
    for offset in chess.pgn.scan_offsets(StringIO.StringIO(s)):
        lines.extend(split_pgn(s[offset:], turn))
    return lines


def split_pgn(s, turn):
    g = chess.pgn.read_game(StringIO.StringIO(s))
    curline = []
    lines = []
    seen = set()

    def rec_split(node):
        nrchildren = len(node.variations)
        if nrchildren == 0:
            fen = node.board().fen()
            if fen not in seen:
                seen.add(fen)
                lines.append(curline[:])

        okmoves = None
        if nrchildren > 1:
            okmoves = [v.san() for v in node.variations]

        for v in node.variations:
            d = {'move': v.san()}
            if okmoves:
                ok2 = okmoves[:]
                ok2.remove(v.san())
                d['ok'] = ok2
            if turn == node.board().turn:
                d['ask'] = True
            if v.comment.strip():
                d['comment'] = v.comment.strip()
            curline.append(d)
            rec_split(v)
            curline.pop()

    rec_split(g)
    return lines

if __name__ == '__main__':
    import sys
    print split_pgn(open(sys.argv[1]).read(), sys.argv[2] == 'w')
