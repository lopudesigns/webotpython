#!/usr/bin/env python3

from . import util

import argparse
import hashlib
import json
import sys

def process_esc(s, esc="", resolver=None):
    result = []
    for e, is_escaped in util.tag_escape_sequences(s, esc):
        if not is_escaped:
            result.append(e)
            continue
        ktype, seed = e.split(":", 1)
        if ktype == "publickey":
            result.append( json.dumps(resolver.get_pubkey(seed))[1:-1] )
        elif ktype == "privatekey":
            result.append( json.dumps(resolver.get_privkey(seed))[1:-1] )
        else:
            raise RuntimeError("invalid input")
    return "".join(result)

def get_key_from_seed(seed):
    """ Use ECDSA library here. """
    return PrivateKey(hashlib.sha256(seed.encode("ascii")).hexdigest())

class ProceduralKeyResolver(object):
    """
    Every synthetic testnet key is generated by concatenating the name, secret and role.
    This class is the central place these are issued, and keeps track of all of them.
    """
    def __init__(self, secret="", keyprefix="TST"):
        self.seed2pair = {}
        self.secret = secret
        self.keyprefix = keyprefix
        return

    def get(self, seed=""):
        pair = self.seed2pair.get(seed)
        if pair is None:
            priv = get_key_from_seed(self.secret+seed)
            pub = format(priv.pubkey, self.keyprefix)
            wif = format(priv, "wif")
            pair = (pub, wif)
            self.seed2pair[seed] = pair
        return pair

    def get_pubkey(self, seed):
        return self.get(seed)[0]

    def get_privkey(self, seed):
        return self.get(seed)[1]

def main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description="Resolve procedural keys")
    parser.add_argument("-i", "--input-file", default="-", dest="input_file", metavar="FILE", help="File to read actions from")
    parser.add_argument("-o", "--output-file", default="-", dest="output_file", metavar="FILE", help="File to write actions to")
    args = parser.parse_args(argv[1:])

    if args.output_file == "-":
        output_file = sys.stdout
    else:
        output_file = open(args.output_file, "w")

    if args.input_file == "-":
        input_file = sys.stdin
    else:
        input_file = open(args.input_file, "r")

    resolver = ProceduralKeyResolver()

    for line in input_file:
        line = line.strip()
        act, act_args = json.loads(line)
        if act == "set_secret":
            resolver.secret = act_args["secret"]
            continue
        esc = act_args.get("esc")
        if esc:
            act_args_minus_esc = dict(act_args)
            del act_args_minus_esc["esc"]
            json_line_minus_esc = json.dumps([act, act_args_minus_esc], separators=(",", ":"), sort_keys=True)
            line = process_esc(json_line_minus_esc, esc=esc, resolver=resolver)
        output_file.write(line)
        output_file.write("\n")
        output_file.flush()
    if args.input_file != "-":
        input_file.close()
    if args.output_file != "-":
        output_file.close()

if __name__ == "__main__":
    main(sys.argv)
