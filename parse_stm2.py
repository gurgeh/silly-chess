# coding: utf-8

from pyparsing import alphanums, oneOf, Word, OneOrMore, Or, QuotedString, Literal


def String():
    return Or([QuotedString('{', escChar='\\', endQuoteChar='}', multiline=True), Word(alphanums + 'åäöÅÄÖ!.,,;?-_:*+()[]%&#"\'')])

header = Literal("set ::tree::mask::maskSerialized").suppress()

position = Literal('{').suppress() + Word(alphanums + '/') + oneOf(['b', 'w']) + \
    Word('KQkq-') + Word(alphanums + '-') + Literal('}').suppress()
move = Literal('{').suppress() + Word(alphanums + '=+-') + String() + String() + \
    String() + String() + String() + Literal('}').suppress()
moves = Literal(
    '{{').suppress() + OneOrMore(move, ' ') + Literal('} {}}')
posmoves = position + moves
positions = Literal(
    '{').suppress() + OneOrMore(posmoves) + Literal('}').suppress()

STM = header + positions


def postodict(parsed_pos):
    return {'%s %s %s %s 0 1' % tuple(p[0]): p[1] for p in parsed_pos}


def parseSTM(f):
    xs = STM.parseFile(f)
    state = 'pos'
    moves = []
    i = 0
    while True:
        if i >= len(xs):
            break
        if state == 'pos':
            pos = xs[i:i + 4]
            state = 'moves'
            i += 4
        else:
            if xs[i] == '} {}}':
                yield pos, moves
                moves = []
                state = 'pos'
                i += 1
            else:
                if xs[i] != 'null':
                    moves.append((xs[i], xs[i + 3].decode('utf8')))
                i += 6
