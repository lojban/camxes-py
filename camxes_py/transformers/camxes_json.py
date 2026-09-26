
# pylint: disable=I0011, C0111, C0302, too-few-public-methods, no-self-use, too-many-public-methods, invalid-name, unused-argument

from collections.abc import Sequence
from itertools import chain

from ..parsimonious_ext.expression_nodes import ALTERNATION, LITERAL, LOOKAHEAD, OPTIONAL, REGEX, STAR

from parsimonious.nodes import NodeVisitor, Node

def generic_named_node(node, visited_children, name=None):
    node_name = name or node.expr_name
    children = _children(node, visited_children)
    return _node(node_name, children)

# Emulate pegjs handling of children for ALTERNATION, OPTIONAL and REGEX nodes.
#
# * alternation (/): yield nodes, with the selected option as child
#
# * optional (?): yield nodes with the matched value as child,
#   or with "" as child if no value is matched
#
# * regex (~""): yield matched text as child
#
def _children(node, visited_children):
    node_type = node.node_type()

    if node_type == ALTERNATION:
        return _child_if_singleton(visited_children)
    elif node_type == OPTIONAL:
        child = _child_if_singleton(visited_children)
        return child if _is_js_truthy(child) else ""
    elif node_type == REGEX:
        return node.text

    return visited_children

def _child_if_singleton(children):
    if isinstance(children, list) and len(children) == 1:
        return children[0]
    return None

# javascript arrays (python lists/sequences) are truthy, even when empty
def _is_js_truthy(obj):
    if isinstance(obj, str) or not isinstance(obj, Sequence):
        return bool(obj)
    # non-string sequences are true in JavaScript, even when empty
    return True

def generic_anonymous_node(node, visited_children):
    node_type = node.node_type()
    if node_type == LITERAL or node_type == REGEX:
        return node.text
    else:
        return _children(node, visited_children)

def join(node, visited_children):
    children = _children(node, visited_children)
    return _join(children)

# camxes-js: _join(arg)
def _join(children):
    if isinstance(children, str):
        return children
    elif _is_js_truthy(children):
        ret = ""
        for child in children:
            # FIXME: transform children?
            if _is_js_truthy(child):
                child_str = _join(child)
                # _join may return None
                if isinstance(child_str, str):
                    ret += child_str
        return ret
    return None

# specialized wrapper for: _node_empty(label, arg)
def node_elidible(node, visited_children, name=None):
    node_name = name or node.expr_name
    optional_node_name = node_name.replace("_elidible", "")
    children = _children(node, visited_children)
    return [optional_node_name] \
            if children == "" or not _is_js_truthy(children) \
            else _node_empty(node_name, children)

# camxes-js: _node_empty(label, arg)
def _node_empty(node_name, children):
    if _has_nonblank_head(children):
        return [node_name, children] if node_name else [children]
    elif not _is_js_truthy(children):
        return [node_name] if node_name else []
    # children is likely a string, and empty list, or a list with a blank head
    # reduce to string, [node_name], or []
    return _node_int(node_name, children)

def _has_nonblank_head(children):
    return isinstance(children, list)        \
            and len(children) > 0            \
            and isinstance(children[0], str) \
            and children[0]

# camxes-js: _node_int(label, arg)
def _node_int(node_name, children):
    if isinstance(children, str):
        return children
    ret = [] if node_name == None else [node_name]
    if _is_js_truthy(children):
        for child in children:
            if _is_js_truthy(child) and len(child) != 0:
                unwrapped_child = _node_int(None, child)
                ret.append(unwrapped_child)
    return ret

# camxes-js: _node(label, arg)
def _node(node_name, children):
    pruned = _node_empty(node_name, children)
    return [] if len(pruned) == 1 and node_name else pruned

# "_lg" for "Leftwise Grouping".
def node_lg(node, visited_children, name=None):
    node_name = name or node.expr_name
    children = _children(node, visited_children)
    return _node_lg(node_name, children)

# camxes-js: _node_lg(label, arg)
def _node_lg(node_name, children):
    flattened_children = _flatten_node(children)
    grouped_children = _group_leftwise(flattened_children)
    return _node(node_name, grouped_children)

# camxes-js: _flatten_node(children)
# Flatten nameless nodes (but not in place!)
# e.g. [Name1, [[Name2, X], [Name3, Y]]] --> [Name1, [Name2, X], [Name3, Y]]
def _flatten_node(children):
    if not isinstance(children, list):
        return children
    flat_children = []
    for child in children:
        if isinstance(child, list):
            if len(child) > 0:
                if isinstance(child[0], list):
                    flat_child = _flatten_node(child)
                    flat_children.extend(flat_child)
                else:
                    flat_children.append(child)
        else:
            flat_children.append(child)
    return flat_children

# camxes-js: _group_leftwise(arr)
def _group_leftwise(children):
    if not isinstance(children, list):
        return []
    elif len(children) <= 2:
        return children
    head, tail = children[0:-1], children[-1]
    grouped_head = _group_leftwise(head)
    return [grouped_head, tail]

def node_lg2(node, visited_children, name=None):
    node_name = name or node.expr_name
    children = _children(node, visited_children)
    return _node_lg2(node_name, children)

# camxes-js: _node_lg2(label, arg)
def _node_lg2(node_name, children):
    if isinstance(children, list) and len(children) == 2:
        seq = children[0]
        concatenated_children = _js_concat(children[0], children[1])
        grouped_children = _group_leftwise(concatenated_children)
    else:
        grouped_children = _group_leftwise(children)
    return _node(node_name, grouped_children)

# JavaScript will concat arrays to strings and vice-versa
# This method always returns new objects
def _js_concat(seq, other):
    if isinstance(seq, list):
        return _js_concat_array(seq, other)
    elif isinstance(seq, str):
        return _js_concat_string(seq, other)
    else:
        raise f"Can't concat non-list/str {seq}"

def _js_concat_array(orig, other):
    copied = orig.copy()
    if isinstance(other, list):
        copied.extend(other)
    else:
        copied.append(other)
    return copied

def _js_concat_string(seq, other):
    if isinstance(other, list):
        flattened_list = list(chain.from_iterable(other))
        other_str = ",".join(flattened_list)
        return seq + other_str
    else:
        return seq + str(other)

##

class Transformer(object):

    def transform(self, parsed):
        return Visitor().visit(parsed)

class Visitor(NodeVisitor):

    # ___ GRAMMAR ___

     #: LR2 _node_lg2
    def visit_bridi_tail_1(self, node, visited_children):
        return node_lg2(node, visited_children)

     #: LR2 _node_lg2
    def visit_sumti_2(self, node, visited_children):
        return node_lg2(node, visited_children)

    #: LR _node_lg
    def visit_selbri_3(self, node, visited_children):
        return node_lg(node, visited_children)

    #: LR2 _node_lg2
    def visit_selbri_4(self, node, visited_children):
        return node_lg2(node, visited_children)

    # Magic Words

    #: LR _node_lg
    def visit_zei_clause_no_pre(self, node, visited_children):
        return node_lg(node, visited_children)

    #: LR _node_lg
    def visit_bu_clause_no_pre(self, node, visited_children):
        return node_lg(node, visited_children)

    #: LEAF _join
    def visit_dot_star(self, node, visited_children):
        return ["dot_star", join(node, visited_children)]

    #: LR _node_lg
    def visit_pre_clause(self, node, visited_children):
        return node_lg(node, visited_children)

    # ___ ELIDIBLE TERMINATORS ___

    def visit_BEhO_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_BOI_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_CU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_DOhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_FEhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_GEhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_KEI_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_KEhE_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_KU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_KUhE_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_KUhO_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_LIhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_LOhO_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_LUhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_MEhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_NUhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_SEhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_TEhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_TOI_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_TUhU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_VAU_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    def visit_VEhO_elidible(self, node, visited_children):
        return node_elidible(node, visited_children)

    # ___ GRAMMAR ___

    #: PUSH _push (camxes-py: _enhance_zoi_open)
    def visit_zoi_open(self, node, visited_children):
        delimiter = visited_children[1]
        return generic_named_node(node, visited_children)

    #: LEAF _join
    def visit_zoi_word_2(self, node, visited_children):
        return ["zoi_word_2", join(node, visited_children)]

    #: PEEK-DIFF !_peek_eq (camxes-py: _enhance_zoi_word)
    def visit_zoi_word(self, node, visited_children):
        return generic_named_node(node, visited_children)

    #: POP-EQ &_peek_eq, _pop (camxes-py: _enhance_zoi_close)
    def visit_zoi_close(self, node, visited_children):
        return generic_named_node(node, visited_children)

    # ____

    #: JOIN _join
    def visit_comma(self, node, visited_children):
        return join(node, visited_children)

    #: JOIN _join
    def visit_non_space(self, node, visited_children):
        return join(node, visited_children)

    #: JOIN _join
    def visit_space_char(self, node, visited_children):
        return join(node, visited_children)

    # ____

    #: LEAF _join
    def visit_initial_spaces(self, node, visited_children):
        return ["initial_spaces", join(node, visited_children)]

    # ____

    def generic_visit(self, node, visited_children):
        if node.expr_name:
            return generic_named_node(node, visited_children)
        return generic_anonymous_node(node, visited_children)

