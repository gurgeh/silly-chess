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


def split_pgn(s, turn):
    g = chess.pgn.read_game(StringIO.StringIO(s))
    splitter = Splitter(turn)
    g.accept(splitter)
    return splitter.games
