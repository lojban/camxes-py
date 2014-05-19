
from collections import OrderedDict

import parsimonious_ext.node_types # node_type
from parsimonious.nodes import NodeVisitor

KEY_ORDER = {
  "name"     : 1,
  "type"     : 2,
  "text"     : 3,
  "children" : 4
}

class Visitor(NodeVisitor):

  def generic_visit(self, node, visited_children):
    if node.expr_name:
      d = self._named_node(node, visited_children)
    else:
      d = self._anonymous_node(node, visited_children)
    return self._ordered(d)

  def _anonymous_node(self, node, visited_children):
    d = { "type" : node.node_type }
    if node.text:
      d["text"] = node.text
    if visited_children:
      d["children"] = visited_children
    return d

  def _named_node(self, node, visited_children):
    d = self._anonymous_node(node, visited_children)
    d["name"] = node.expr_name
    return d

  def _ordered(self, d):
    return OrderedDict(sorted(d.items(), key=lambda t: KEY_ORDER[t[0]]))

