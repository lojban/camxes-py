
# pylint: disable=I0011, C0111, no-name-in-module, no-self-use, protected-access, no-member

from parsimonious.expressions import Compound
from parsimonious.nodes import Node

# Note: does not consult the cache

LOOKAHEAD_PREDICATE = "LOOKAHEAD_PREDICATE"

class LookaheadPredicate(Compound):

    NODE_TYPE = LOOKAHEAD_PREDICATE

    def match_core(self, text, pos, cache, error):
        node = self.members[0].match_core(text, pos, cache, error)
        if node is not None and self.evaluate(node):
            return Node(self, text, pos, pos) # like lookahead
        else:
            return None

