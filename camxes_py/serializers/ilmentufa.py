import re
import json

# a port of ilmentufa/camxes_postproc

ACTION_DEL      = "DEL"
ACTION_FLATTEN  = "FLAT"
ACTION_PASS     = "PASS"
ACTION_TRIM     = "TRIM"
ACTION_TRIMFLAT = "TRIMFLAT"
ACTION_UNBOX    = "UNBOX"

SPECIAL_RULES = ["cmevla", "gismu", "lujvo", "fuhivla", "ga_clause", "gu_clause"]
SPACE_RULES = ["spaces", "initial_spaces"]

NODE_LABELS = ["prenex", "sentence", "selbri", "sumti"]

SPACE_SUBSTITUTION = {
    "spaces": "_",
    "initial_spaces": "_"
}

NAME_SUBSTITUTION = {
    "cmene": "C",
    "cmevla": "C",
    "gismu": "G",
    "lujvo": "L",
    "fuhivla": "Z",
    "prenex": "PRENEX",
    "sentence": "BRIDI",
    "selbri": "SELBRI",
    "sumti": "SUMTI"
}

PATTERN_SELMAHO = r"^[IUBCDFGJKLMNPRSTVXZ]?([AEIOUY]|(AI|EI|OI|AU))(h([AEIOUY]|(AI|EI|OI|AU)))*$"

class SerializerConfig(object):

    def __init__(self,
                 with_spaces = False,
                 with_morphology = False,
                 with_terminators = False,
                 with_trimming = True, # opposite of "R" mode
                 with_selmaho = False,
                 with_nodes_labels = False,
                 with_json_format = False,
                 with_indented_json = False,
                 without_leaf_prefix = False,
                 # passing a glosser implies with_glossing == True
                 # glosser implements describe(source: str): str
                 with_glosser = None):
        self.with_spaces = with_spaces
        self.with_morphology = with_morphology
        self.with_terminators = with_terminators
        self.with_trimming = with_trimming
        self.with_selmaho = with_selmaho
        self.with_nodes_labels = with_nodes_labels
        self.with_json_format = with_json_format
        self.with_indented_json = with_indented_json
        self.without_leaf_prefix = without_leaf_prefix

class Serializer(object):

    def __init__(self, config=None):
        self.config = config or TransformerConfig()

    def dumps(self, transformed):
        serialized = postprocess_node(transformed, self.config)
        if serialized == None:
            serialized = []

        json_indent = 2 if self.config.with_indented_json else None
        serialized = json.dumps(serialized, separators=(",", ":"), indent=json_indent)
        if self.config.with_json_format or self.config.with_indented_json:
            return serialized

        return format_text(serialized, self.config)

##

# process_parse_tree
def postprocess_node(node, config):
    if len(node) == 0:
        return None

    action = node_action_for(node, config)
    if (action == ACTION_DEL):
        return None

    substitution_value = substitution_values(config).get(node[0]) \
            if is_named_node(node) else None
    if is_named_node(node):
        if action == ACTION_TRIM:
            if substitution_value != None:
                return substitution_value
            del node[0]
        else:
            node_alias = substitution_names(config).get(node[0])
            if node_alias != None:
                node[0] = node_alias
            if substitution_value != None:
                return [node[0], substitution_value]

    if action == ACTION_FLATTEN:
        return flatten_node(node, config)
    elif action == ACTION_TRIMFLAT:
        return join_expr(node)

    node_length = postprocess_tail(node, config)
    if node_length == 0:
        return None
    elif node_length == 1 and action != ACTION_PASS:
        if config.with_glosser:
            node[0] = apply_gloss(config.with_glosser, node[0])
        return node[0]
    elif must_prefix_leaf_nodes(config) and node_length == 2 and is_named_node(node) and isinstance(node[1], str):
        if not ":" in node[1]:
            return node[0] + ":" + node[1]
        else:
            node[0] += ":"

    return node

def node_action_for(node, config):
    if is_branch_removal_target(node, config):
        return ACTION_DEL

    ft = is_flattening_target(node, config)
    tt = is_trimming_target(node, config)
    if ft and tt:
        return ACTION_TRIMFLAT
    if ft:
        return ACTION_FLATTEN
    if tt:
        return ACTION_TRIM
    if config.with_trimming and len(node) == 1:
        return ACTION_UNBOX # no downstream references?
    return ACTION_PASS

def is_branch_removal_target(node, config):
    if (not config.with_spaces) and among(node[0], SPACE_RULES):
        return True
    return (not config.with_terminators) and is_selmaho(node[0]) and len(node) == 1

def among(v, s):
    i = 0
    while i < len(s):
        if s[i] == v:
            return True
        i += 1
    return False

def is_selmaho(name):
    if not isinstance(name, str):
        return False
    return re.match(PATTERN_SELMAHO, name) != None

def is_flattening_target(node, config):
    if config.with_morphology:
        return False
    return among(node[0], SPECIAL_RULES) or is_selmaho(node[0])

# is_node_trimming_target
def is_trimming_target(node, config):
    if not config.with_trimming:
        return False
    if config.with_terminators and is_selmaho(node[0]) and len(node) == 1:
        return False
    if config.with_selmaho and is_selmaho(node[0]):
        return False
    return not is_whitelisted(node[0], config)

def is_whitelisted(name, config):
    if config.with_selmaho:
        if among(name, SPECIAL_RULES):
            return True
    if config.with_nodes_labels:
        return among(name, NODE_LABELS)

def substitution_values(config):
    if config.with_spaces:
        return SPACE_SUBSTITUTION
    return {}

def substitution_names(config):
    if not config.with_trimming:
        return {}
    return NAME_SUBSTITUTION

def is_named_node(node):
    return isinstance(node[0], str)

def apply_gloss(glosser, text):
    # note: ilmentufa assumes glosser is a source-text-keyed object
    gloss = glosser.describe(text)
    return "'" + gloss + "'" if gloss else text

def must_prefix_leaf_nodes(config):
    return (config.with_nodes_labels or config.with_selmaho) \
            and not config.without_leaf_prefix

def flatten_node(node, config):
    joined_tail = join_expr(node)
    if is_named_node(node) and joined_tail != "":
        if must_prefix_leaf_nodes(config):
            return node[0] + ":" + joined_tail
        else:
            return [node[0], joined_tail]
    elif is_named_node(node):
        return node[0]
    else:
        return joined_tail

def join_expr(n):
    if len(n) < 1:
        return ""
    s = ""
    i = 0 if isinstance(n[0], list) else 1
    while i < len(n):
        s += n[i] if isinstance(n[i], str) else join_expr(n[i])
        i += 1
    return s

def postprocess_tail(node, config):
    i = 1 if is_named_node(node) else 0
    while i < len(node):
        if isinstance(node[i], list):
            node[i] = postprocess_node(node[i], config)
        if node[i] == None:
            del node[i]
        else:
            i += 1
    return i

def format_text(output, config):
    output = re.sub(r"\"", "", output, flags=re.MULTILINE)
    if config.with_selmaho:
        output = re.sub(r"\[([a-zA-Z0-9_-]+),\[", "[\1: [", output, flags=re.MULTILINE)
    output = re.sub(r",", " ", output, flags=re.MULTILINE)
    return prettify_brackets(output)

##

OPEN_BRACKETS = ["(", "[", "{", "<"]
CLOSE_BRACKETS = [")", "]", "}", ">"]
BRACKETS_NUMBER = 4
NUMSET = ["\u2070","\u00b9","\u00b2","\u00b3","\u2074",
          "\u2075","\u2076","\u2077","\u2078","\u2079"]

def prettify_brackets(txt):
    i = 0
    floor = 0
    while i < len(txt):
        if txt[i] == "[":
            n = floor % BRACKETS_NUMBER
            num = str_print_uint(floor / BRACKETS_NUMBER, NUMSET) \
                    if (floor and not n) else ""
            txt = str_replace(txt, i, 1, OPEN_BRACKETS[n] + num)
            floor += 1
        elif txt[i] == "]":
            floor -= 1
            n = floor % BRACKETS_NUMBER
            num = str_print_uint(floor / BRACKETS_NUMBER, NUMSET) \
                    if (floor and not n) else ""
            txt = str_replace(txt, i, 1, num + CLOSE_BRACKETS[n])
        i += 1

    return txt

def str_print_uint(val, charset):
    # charset must be a character array
    radix = len(charset)
    txt = ""
    val -= val % 1 # no float allowed
    while val >= 1:
        txt = charset[val % radix] + txt
        val /= radix
        val -= val % 1
    return txt

def str_replace(txt, pos, i, sub):
    if pos < len(txt):
        if pos + i >= len(txt):
            i -= (pos + i - len(txt))
        return txt[0:pos] + sub + txt[pos + i:]
    else:
        return txt

