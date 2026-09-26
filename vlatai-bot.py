#!/usr/bin/env python3

# pylint: disable=I0011, C0111, import-error, bad-whitespace, no-member

import sys

from argparse import ArgumentParser

from twisted.internet import reactor
from twisted.python import log

from camxes import __version__
from irc.protocol_factory import IrcClientFactory

DEFAULT_HOST     = "irc.libera.net"
DEFAULT_PORT     = 6667
DEFAULT_CHANNELS = [ "#lojban" ]
DEFAULT_NICKNAME = "vlatai"
DEFAULT_DISPATCH = "vlatai"

def run(options):
    protocol = _dispatch_protocol(options.dispatch)
    factory = IrcClientFactory(protocol, options)
    log.startLogging(sys.stdout)
    reactor.connectTCP(options.host, options.port, factory)
    reactor.run()

def _dispatch_protocol(dispatch):
    if dispatch == "vlatai":
        from irc.vlatai import Protocol
        return Protocol
    elif dispatch == "morphology":
        from irc.morphology import Protocol
        return Protocol
    else:
        raise ValueError("Unknown dispatch: '%s'" % dispatch)

def _main():
    options = _parse_args()
    if len(options.channels) == 0:
        options.channels = DEFAULT_CHANNELS
    run(options)

def _parse_args():
    args = ArgumentParser()

    args.add_argument("-H", "--host",
                      dest="host", default=DEFAULT_HOST)

    args.add_argument("-p", "--port",
                      dest="port", default=DEFAULT_PORT)

    args.add_argument("-c", "--channels",
                      action="append",
                      dest="channels", default=[])

    args.add_argument("-n", "--name",
                      dest="name", default=DEFAULT_NICKNAME)

    args.add_argument("-d", "--dispatch",
                      dest="dispatch", default=DEFAULT_DISPATCH)

    args.add_argument("-v", "--version",
                      action="version", version=__version__)

    return args.parse_args()

if __name__ == '__main__':
    _main()
