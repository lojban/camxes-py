#!/usr/bin/env python3

# pylint: disable=I0011, C0111, C0326, W0611

import sys
import platform
import json

from optparse import OptionParser

import camxes_py.parsimonious_ext # expression_nodes

__version__ = "v0.11.1"

PARSERS      = [ 'camxes-ilmen' ]
TRANSFORMERS = [ 'camxes-json', 'camxes-morphology', 'minimal', 'vlatai', 'node-coverage', 'debug', 'raw' ]
SERIALIZERS  = [ 'ilmentufa', 'json', 'json-pretty', 'json-compact', 'xml' ]

IMPLEMENTATION_RECURSION_LIMIT = {
    'CPython' : 10000
}

# Texts like this one require 9700-9800 on CPython (CPython default is 1000):
#
#  mo'ini'a mo'ini'a mo'ini'a i ka'e zukte no drata be la'e di'e iseki'ubo
#  la alis za'ure'u co'a tavla i lu ju'o la dinas ba mutce le ka se claxu mi kei
#  ca le cabnicte tosa'a la dinas cu mlatu toi i a'o da ba morji tu'a le dy
#  ladru palna ca le sanmi tcika i doi dinas noi dirba mi do'u au do mi kansa
#  le cnita i u'u no smacu cu zvati le vacri i ku'i do ka'e kavbu lo volratcu
#  noi ka'u mutce le ka simsa lo'e smacu i ku'i a'u xu lo'e mlatu cu citka
#  lo'e volratcu li'u i caku la alis co'a sipydji lifri gi'e di'a senva sezysku
#  lu xu lo'e mlatu cu citka lo'e volratcu i xu lo'e mlatu cu citka lo'e
#  volratcu li'u esu'oroibo lu xu lo'e volratcu cu citka lo'e mlatu li'u
#  iseja'ebo na vajni mutce fa le du'u porsi makau ki'u le nu abu ka'e spuda no
#  le re preti i abu lifri le nu pu'o sipna kei gi'e puzi co'a senva le nu abu
#  xanjaisi'u cadzu kansa la dinas gi'e cusku lu ju'i doi dinas ko mi jungau
#  le jetnu i xu do su'oroi citka lo volratcu li'u ca le nu suksa fa le nu abu
#  le cpana be lo derxi be loi grana ku joi loi sudga pezli mo'u farlu
#
# Pypy doesn't need to increase limit; untested on Jython and IronPython

def check_parser_option(option, _, value, parser):
    if value in PARSERS:
        setattr(parser.values, option.dest, value)
    else:
        bad_parser()

def bad_parser():
    raise ValueError("Value for parser must be one of: %s" % \
        (", ".join(PARSERS)))

def check_transformer_option(option, _, value, parser):
    if value in TRANSFORMERS:
        setattr(parser.values, option.dest, value)
    else:
        bad_transformer()

def bad_transformer():
    raise ValueError("Value for transformer must be one of: %s" % \
        (", ".join(TRANSFORMERS)))

def check_serializer_option(option, _, value, parser):
    if value in SERIALIZERS:
        setattr(parser.values, option.dest, value)
    else:
        bad_serializer()

def bad_serializer():
    raise ValueError("Value for serializer must be one of: %s" % \
        (", ".join(SERIALIZERS)))

def configure_platform():
    impl = platform.python_implementation()
    if impl in IMPLEMENTATION_RECURSION_LIMIT:
        stack_limit = IMPLEMENTATION_RECURSION_LIMIT[impl]
        sys.setrecursionlimit(stack_limit)

def run(text, options):
    parser = build_parser(options)
    parsed = parser.parse(text)
    transformer = build_transformer(options.transformer, parser)
    transformed = transformer.transform(parsed)
    print(serialize(transformed,
                    options.serializer,
                    default_object_serializer(transformer)))

def build_parser(options):
    parser_option = options.parser if len(PARSERS) > 1 else "camxes-ilmen"
    if parser_option == 'camxes-ilmen':
        from camxes_py.parsers import camxes_ilmen
        return camxes_ilmen.Parser(options.rule)
    else:
        bad_parser()

def build_transformer(transformer_option, parser):
    if transformer_option == 'camxes-json':
        from camxes_py.transformers import camxes_json
        return camxes_json.Transformer()
    elif transformer_option == 'camxes-morphology':
        from camxes_py.transformers import camxes_morphology
        return camxes_morphology.Transformer()
    elif transformer_option == 'vlatai':
        from camxes_py.transformers import vlatai
        return vlatai.Transformer()
    elif transformer_option == 'minimal':
        from camxes_py.transformers import minimal
        return minimal.Transformer()
    elif transformer_option == 'node-coverage':
        from camxes_py.transformers import node_coverage
        return node_coverage.Transformer(parser)
    elif transformer_option == 'debug':
        from camxes_py.transformers import debug
        return debug.Transformer()
    elif transformer_option == 'raw':
        from camxes_py.transformers import raw
        return raw.Transformer()
    else:
        bad_transformer()

def default_object_serializer(transformer):
    if hasattr(transformer, 'default_serializer'):
        return transformer.default_serializer()
    else:
        return lambda x: x.__dict__

def serialize(transformed, fmt, default_serializer):
    if fmt == 'json':
        return json.dumps(transformed,
                          default=default_serializer)
    elif fmt == 'json-compact':
        return json.dumps(transformed,
                          separators=(',', ':'),
                          default=default_serializer)
    elif fmt == 'ilmentufa':
        from camxes_py.serializers import ilmentufa
        config = ilmentufa.SerializerConfig(with_trimming=False, with_json_format=True)
        serializer = ilmentufa.Serializer(config)
        return serializer.dumps(transformed)
    elif fmt == 'json-pretty':
        return json.dumps(transformed,
                          indent=4,
                          default=default_serializer)
    elif fmt == 'xml':
        from camxes_py.serializers import xml
        return xml.dumps(transformed)
    else:
        bad_serializer()

def _main():
    (params, argv) = _parse_args()
    text = " ".join(argv)
    configure_platform()
    run(text, params)

def _parse_args():
    usage_fmt = "usage: %prog [ options ] { input }"
    options = OptionParser(usage=usage_fmt, version="%prog " + __version__)

    if len(PARSERS) > 1:
        options.add_option("-p", "--parser",
                           help=("options: %s" % (", ".join(PARSERS))) + \
                             " [default: %default]",
                           type="string", action="callback",
                           dest="parser", default="camxes-ilmen",
                           callback=check_parser_option)

    options.add_option("-t", "--transformer",
                       help=("options: %s" % (", ".join(TRANSFORMERS))) + \
                         " [default: %default]",
                       type="string", action="callback",
                       dest="transformer", default="camxes-json",
                       callback=check_transformer_option)

    options.add_option("-s", "--serializer",
                       help=("options: %s" % (", ".join(SERIALIZERS))) + \
                         " [default: %default]",
                       type="string", action="callback",
                       dest="serializer", default="ilmentufa",
                       callback=check_serializer_option)

    options.add_option("-r", "--rule",
                       type="string", action="store",
                       dest="rule")

    return options.parse_args()

if __name__ == '__main__':
    _main()
