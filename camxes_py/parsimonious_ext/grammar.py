
# pylint: disable=I0011, C0111, C0326, too-many-arguments, protected-access

"""
Applies modified pull request 141 (ensure all LazyReference objects are resolved)
_find_unresolved is removed since it led to grammar load times of >1 minute
+TODO: remove once upgraded to parsimonious v10, which includes this patch
"""

from functools import partial, wraps
from collections import OrderedDict
from six import text_type

from parsimonious.grammar import RuleVisitor, LazyReference
from parsimonious.exceptions import UndefinedLabel

from .util import add_to_class, with_original, renamed

@add_to_class(RuleVisitor)
def _resolve_refs(self, rule_map, expr, resolved):
    """Return an expression with all its lazy references recursively
    resolved.
    Resolve any lazy references in the expression ``expr``, recursing into
    all subexpressions.
    :arg done: The set of Expressions that have already been or are
        currently being resolved, to ward off redundant work and prevent
        infinite recursion for circular refs
    """
    if expr in resolved:
        newref = resolved[expr]
    elif isinstance(expr, LazyReference):
        label = text_type(expr)
        try:
            reffed_expr = rule_map[label]
        except KeyError:
            raise UndefinedLabel(expr)
        newref = resolved[expr] = self._resolve_refs(rule_map, reffed_expr, resolved)
    else:
        if getattr(expr, 'members', ()) and expr not in resolved:
            # Prevents infinite recursion for circular refs. At worst, one
            # of `expr.members` can refer back to `expr`, but it can't go
            # any farther.
            resolved[expr] = expr
            expr.members = tuple(self._resolve_refs(rule_map, member, resolved)
                                 for member in expr.members)
        newref = expr
    return newref

@add_to_class(RuleVisitor)
def visit_rules(self, node, rules_list):
    """Collate all the rules into a map. Return (map, default rule).
    The default rule is the first one. Or, if you have more than one rule
    of that name, it's the last-occurring rule of that name. (This lets you
    override the default rule when you extend a grammar.) If there are no
    string-based rules, the default rule is None, because the custom rules,
    due to being kwarg-based, are unordered.
    """
    _, rules = rules_list

    # Map each rule's name to its Expression. Later rules of the same name
    # override earlier ones. This lets us define rules multiple times and
    # have the last declaration win, so you can extend grammars by
    # concatenation.
    rule_map = OrderedDict((expr.name, expr) for expr in rules)

    # And custom rules override string-based rules. This is the least
    # surprising choice when you compare the dict constructor:
    # dict({'x': 5}, x=6).
    rule_map.update(self.custom_rules)

    # Resolve references. This tolerates forward references.
    # We use a job pool `to_resolve` to remember all rules to resolve. It is
    # initialized with all existing rules in `rule_map` and all
    # LazyReference rules found later will be added as well.
    resolved = {}

    rule_map = OrderedDict((expr.name, self._resolve_refs(rule_map, expr, resolved))
                           for expr in rule_map.values())

    # isinstance() is a temporary hack around the fact that * rules don't
    # always get transformed into lists by NodeVisitor. We should fix that;
    # it's surprising and requires writing lame branches like this.
    return rule_map, (rule_map[rules[0].name]
                      if isinstance(rules, list) and rules else None)

