#!/usr/bin/env python2
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

# Exercise the listtransactions API

import pdb
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework import BitcoinTestFramework
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from util import *
from test_framework.mininode import CTransaction, COIN
from io import BytesIO

def txFromHex(hexstring):
    tx = CTransaction()
    f = BytesIO(hex_str_to_bytes(hexstring))
    tx.deserialize(f)
    return tx

def check_array_result(object_array, to_match, expected):
    """
    Pass in array of JSON objects, a dictionary with key/value pairs
    to match against, and another dictionary with expected key/value
    pairs.
    """
    num_matched = 0
    for item in object_array:
        all_match = True
        for key,value in to_match.items():
            if item[key] != value:
                all_match = False
        if not all_match:
            continue
        for key,value in expected.items():
            if item[key] != value:
                raise AssertionError("%s : expected %s=%s"%(str(item), str(key), str(value)))
            num_matched = num_matched+1
    if num_matched == 0:
        raise AssertionError("No objects matched %s"%(str(to_match)))

class ListTransactionsTest(BitcoinTestFramework):

    def setup_nodes(self):
        enable_mocktime()
        return start_nodes(4, self.options.tmpdir)

    def run_test(self):
        # Simple send, 0 to 1:
        txid = self.nodes[0].sendtoaddress(self.nodes[1].getnewaddress(), 0.1)
        self.sync_all()
        check_array_result(self.nodes[0].listtransactions(),
                           {"txid":txid},
                           {"category":"send","account":"","amount":Decimal("-0.1"),"confirmations":0})
        check_array_result(self.nodes[1].listtransactions(),
                           {"txid":txid},
                           {"category":"receive","account":"","amount":Decimal("0.1"),"confirmations":0})
        # mine a block, confirmations should change:
        self.nodes[0].setgenerate(True, 1)
        self.sync_all()
        check_array_result(self.nodes[0].listtransactions(),
                           {"txid":txid},
                           {"category":"send","account":"","amount":Decimal("-0.1"),"confirmations":1})
        check_array_result(self.nodes[1].listtransactions(),
                           {"txid":txid},
                           {"category":"receive","account":"","amount":Decimal("0.1"),"confirmations":1})

        # send-to-self:
        txid = self.nodes[0].sendtoaddress(self.nodes[0].getnewaddress(), 0.2)
        check_array_result(self.nodes[0].listtransactions(),
                           {"txid":txid, "category":"send"},
                           {"amount":Decimal("-0.2")})
        check_array_result(self.nodes[0].listtransactions(),
                           {"txid":txid, "category":"receive"},
                           {"amount":Decimal("0.2")})

        # sendmany from node1: twice to self, twice to node2:
        send_to = { self.nodes[0].getnewaddress() : 0.11,
                    self.nodes[1].getnewaddress() : 0.22,
                    self.nodes[0].getaccountaddress("from1") : 0.33,
                    self.nodes[1].getaccountaddress("toself") : 0.44 }
        txid = self.nodes[1].sendmany("", send_to)
        self.sync_all()
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"send","amount":Decimal("-0.11")},
                           {"txid":txid} )
        check_array_result(self.nodes[0].listtransactions(),
                           {"category":"receive","amount":Decimal("0.11")},
                           {"txid":txid} )
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"send","amount":Decimal("-0.22")},
                           {"txid":txid} )
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"receive","amount":Decimal("0.22")},
                           {"txid":txid} )
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"send","amount":Decimal("-0.33")},
                           {"txid":txid} )
        check_array_result(self.nodes[0].listtransactions(),
                           {"category":"receive","amount":Decimal("0.33")},
                           {"txid":txid, "account" : "from1"} )
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"send","amount":Decimal("-0.44")},
                           {"txid":txid, "account" : ""} )
        check_array_result(self.nodes[1].listtransactions(),
                           {"category":"receive","amount":Decimal("0.44")},
                           {"txid":txid, "account" : "toself"} )
        multisig = self.nodes[1].createmultisig(1, [self.nodes[1].getnewaddress()])
        self.nodes[0].importaddress(multisig["redeemScript"], "watchonly", False, True)
        txid = self.nodes[1].sendtoaddress(multisig["address"], 0.1)
        self.nodes[1].generate(1)
        self.sync_all()
        assert(len(self.nodes[0].listtransactions("watchonly", 100, 0, False)) == 0)
        assert_array_result(self.nodes[0].listtransactions("watchonly", 100, 0, True),
                           {"category":"receive","amount":Decimal("0.1")},
                           {"txid":txid, "account" : "watchonly"} )

if __name__ == '__main__':
    ListTransactionsTest().main()

