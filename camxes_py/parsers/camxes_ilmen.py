
# pylint: disable=I0011, C0111, too-many-function-args

import os

from parsimonious.grammar import Grammar

from ..parsimonious_ext.expressions import LookaheadPredicate

GRAMMAR_FILENAME = "camxes_ilmen.peg"

ZOI_DELIMITER_KEY = "zoi_delimiter"

def build_grammar(path):
    with open(path) as handle:
        grammar = Grammar(handle.read())
    return grammar

def _default_grammar_path():
    pwd = os.path.dirname(__file__)
    return os.path.join(pwd, GRAMMAR_FILENAME)

# Not really a predicate: Just capturing delimiter as side effect
class ZoiCaptureDelimiterPredicate(LookaheadPredicate):

    def __init__(self, member, quotation_state):
        super(ZoiCaptureDelimiterPredicate, self).__init__(member)
        self.quotation_state = quotation_state

    def evaluate(self, node):
        self.quotation_state[ZOI_DELIMITER_KEY] = node.text
        return True

class ZoiQuotedWordPredicate(LookaheadPredicate):

    def __init__(self, member, quotation_state):
        super(ZoiQuotedWordPredicate, self).__init__(member)
        self.quotation_state = quotation_state

    def evaluate(self, node):
        return node.text != self.quotation_state[ZOI_DELIMITER_KEY]

# Is this lojban word the zoi quotation delimiter?
class ZoiDelimiterPredicate(LookaheadPredicate):

    def __init__(self, member, quotation_state):
        super(ZoiDelimiterPredicate, self).__init__(member)
        self.quotation_state = quotation_state

    def evaluate(self, node):
        return node.text == self.quotation_state[ZOI_DELIMITER_KEY]

class Parser(object):

    def __init__(self, default_rule=None, path=None):
        if not path:
            path = _default_grammar_path()
        self.grammar = build_grammar(path)
        self._enhance_grammar(default_rule)

    def _enhance_grammar(self, default_rule):
        if default_rule is not None:
            self._apply_default_rule(default_rule)
        self._add_zoi_quotation_handling()

    def _apply_default_rule(self, rule_name):
        try:
            rule = self.grammar[rule_name]
        except KeyError:
            raise ValueError("'%s' is not a rule" % rule_name)
        self.grammar.default_rule = rule

    def _add_zoi_quotation_handling(self):
        quotation_state = {}
        self._enhance_zoi_open(quotation_state)
        self._enhance_zoi_word(quotation_state)
        self._enhance_zoi_close(quotation_state)

    @staticmethod
    def _rewrite_tuple(vals, i, new):
        return tuple((new if i == j else val) for j, val in enumerate(vals))

    # zoi_open = ( &lojban_word lojban_word )
    def _enhance_zoi_open(self, quotation_state):
        zoi_open = self.grammar['zoi_open']
        # zoi_open.members: (<Lookahead &lojban_word>, <OneOf lojban_word = CMEVLA / CMAVO / BRIVLA>)
        lojban_word_lookahead = zoi_open.members[0]
        lojban_word = lojban_word_lookahead.members[0]
        zoi_open_predicate = ZoiCaptureDelimiterPredicate(lojban_word, quotation_state)
        # replace &lojban_word in zoi_open Sequence with ZoiCaptureDelimiterPredicate(lojban_word)
        zoi_open.members = self._rewrite_tuple(zoi_open.members, 0, zoi_open_predicate)

    def _enhance_zoi_word(self, quotation_state):
        zoi_word = self.grammar['zoi_word']
        # zoi_word.members: (<Lookahead &zoi_word_2>, <OneOrMore zoi_word_2 = non_space+>)
        zoi_word_2_lookahead = zoi_word.members[0]
        zoi_word_2 = zoi_word_2_lookahead.members[0]
        zoi_word_predicate = ZoiQuotedWordPredicate(zoi_word_2, quotation_state)
        # replace &zoi_word_2 node in zoi_word Sequence with ZoiQuotedWordPredicate(&zoi_word_2)
        zoi_word.members = self._rewrite_tuple(zoi_word.members, 0, zoi_word_predicate)

    def _enhance_zoi_close(self, quotation_state):
        zoi_close = self.grammar['zoi_close']
        # zoi_close.members: (<Lookahead &any_word>, <Sequence any_word = lojban_word spaces?>)
        any_word_lookahead = zoi_close.members[0]
        any_word = any_word_lookahead.members[0]
        lojban_word = any_word.members[0]
        zoi_close_predicate = ZoiDelimiterPredicate(lojban_word, quotation_state)
        # replace &any_word in zoi_close_sequence with ZoiDelimiterPredicate(lojban_word)
        # (trailing spaces? of any_word will still be consumed by zoi_close.members[1])
        zoi_close.members = self._rewrite_tuple(zoi_close.members, 0, zoi_close_predicate)

    def parse(self, text):
        return self.grammar.parse(text)

    def match(self, text, pos=0):
        return self.grammar.match(text, pos)

