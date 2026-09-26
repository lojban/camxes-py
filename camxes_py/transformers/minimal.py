
# pylint: disable=I0011, C0111, C0326, no-self-use, unused-argument, invalid-name

import re

from parsimonious.nodes import NodeVisitor

def is_selmaho_expression(name):
    return re.match(r"^[ABCDFGIJKLMNPRSTUVXYZ]([AEIOUY]([IU]|h[AEIOU])?)?$", name)

class Transformer(object):

    def transform(self, parsed):
        return Visitor().visit(parsed)

    def default_serializer(self):
        return lambda x : x.as_json()

class Visitor(NodeVisitor):

    def visit_space_char(self, node, visited_children):
        return None

    def visit_EOF(self, node, visited_children):
        return None

    def visit_CMEVLA(self, node, visited_children):
        return ['CMEVLA', node.text]

    def visit_zoi_word(self, node, visited_children):
        return ['zoi_word', node.text]

    def visit_gismu(self, node, visited_children):
        return ['gismu', node.text]

    def visit_lujvo(self, node, visited_children):
        return ['lujvo', node.text]

    def visit_fuhivla(self, node, visited_children):
        return ["fu'ivla", node.text]

    def generic_visit(self, node, visited_children):
        # Catch all the cmavo
        if node.expr_name and is_selmaho_expression(node.expr_name):
            return [node.expr_name, node.text]

        # Catch all the spaces
        if node.expr_name == "" and node.text.strip() == "":
            return None

        # Drop the crap
        proper_children = list(filter(None, visited_children))

        if len(proper_children) == 0:
            if len(node.text) > 0:
                return [node.expr_name, node.text]
            else:
                return None
        else:
            # Make a tree
            if len(proper_children) == 1:
                # Catch the special case where an empty name got used
                # *and* we're the only parent so we can use our name
                if len(proper_children[0]) > 1 and proper_children[0][0] == "":
                    proper_children[0][0] = node.expr_name

                return proper_children[0]
            else:
                # Catch empty names that we *can't* replace because
                # we're not the only parent by just dropping that
                # layer (this happens with ZOI clauses, for example)

                new_children = []
                for child in proper_children:
                    if len(child) > 1 and child[0] == "":
                        new_children.append(child[1])
                    else:
                        new_children.append(child)

                return [node.expr_name, list(new_children)]
