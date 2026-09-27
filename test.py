#!/usr/bin/env python3

# pylint: disable=I0011, C0111, C0326

import os
import json

from collections import OrderedDict

from parsimonious.exceptions import ParseError

from camxes import __version__, configure_platform
from camxes_py.parsers import camxes_ilmen
from camxes_py.transformers import camxes_json
from camxes_py.serializers import ilmentufa

PARSER = "camxes-py"
TRANSFORMER = "camxes-json"
SERIALIZER  = "ilmentufa-notrim-json" # camxes.js -m JR

ENV = OrderedDict([
    ("engine", PARSER),
    ("version", __version__),
    ("format", TRANSFORMER),
    ("serialization", SERIALIZER)
])

TEST_DIRECTORY  = "test"
INPUT_FILENAME  = "camxes_ilmen_js.json"
OUTPUT_FILENAME = "camxes_ilmen_py.json"

PWD = os.path.dirname(__file__)
INPUT_PATH = os.path.join(PWD, TEST_DIRECTORY, INPUT_FILENAME)
OUTPUT_PATH = os.path.join(PWD, TEST_DIRECTORY, OUTPUT_FILENAME)

def main():
    input_json = read_json(INPUT_PATH)
    specs = process_input(input_json)
    dump_results(specs, OUTPUT_PATH)

def read_json(path):
    with open(path) as input_file:
        input_json = json.load(input_file)
    return input_json

def process_input(input_json):
    parser = camxes_ilmen.Parser() # PARSER
    transformer = camxes_json.Transformer() # TRANSFORMER
    serializer_config = ilmentufa.SerializerConfig(with_trimming=False, with_json_format=True)
    serializer = ilmentufa.Serializer(serializer_config) # SERIALIZER

    input_specs = input_json["specs"]
    return [
        process_spec(spec, parser, transformer, serializer) \
            for spec in input_specs
    ]


def process_spec(input_spec, parser, transformer, serializer):
    output_spec = OrderedDict()
    output_spec["md5"] = input_spec["md5"]
    text = output_spec["txt"] = input_spec["txt"]

    out = None
    try:
        print("text: " + text)
        parsed = parser.parse(text)
        transformed = transformer.transform(parsed)
        out = serializer.dumps(transformed)
    except ParseError:
        out = "ERROR"
    if out != input_spec["out"]:
        print_error(text, input_spec["out"], out)
    output_spec["out"] = out

    return output_spec

def serialize(parsed):
    config = ilmentufa.SerializerConfig(with_trimming=False, with_json_format=True)
    serializer = ilmentufa.Serializer(config) # SERIALIZER
    return serialize.dumps(parsed)

def print_error(text, was, now):
    print("----------------")
    print(text)
    print("WAS: %s" % was)
    print("IS:  %s" % now)

def dump_results(specs, output_path):
    with open(output_path, 'w') as output_file:
        results = OrderedDict([
            ("env", ENV),
            ("specs", specs)
        ])
        json.dump(results, output_file, indent=4)

if __name__ == '__main__':
    configure_platform()
    main()
