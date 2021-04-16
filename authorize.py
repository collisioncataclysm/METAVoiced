import sys
import binascii
import json
import uuid
import ipfshttpclient
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from cid import make_cid

# credentials should export a connect string like "http://rpc_user:rpc_password@server:port"
# rpc_user and rpc_password are set in the bitcoin.conf file
import credentials

magic = '0.00001111'
wallet = 'tbtc-wallet.json'    
blockchain = AuthServiceProxy(credentials.tbtc_connect, timeout=120)
ipfs = ipfshttpclient.connect()

try:
    with open(wallet, "r") as read_file:
        db = json.load(read_file)
except:
    db = {}

#print(db)

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal): return float(obj)

def writeWallet(xid, cid, tx):

    n = -1
    for vout in tx['vout']:
        val = vout['value']
        if val.compare(Decimal(magic)) == 0:
            n = vout['n']
            break

    if n < 0:
        print("error, can't find auth txn")
        return

    db[xid] = {
        "cid": cid,
        "auth": { "txid": tx['txid'], "vout": n },
        "tx": tx
    }
    
    with open(wallet, "w") as write_file:
        json.dump(db, write_file, cls = Encoder, indent=4)


def getXid(cid):
    xid = None

    try:
        meta = json.loads(ipfs.cat(cid))
        print(meta)        
        xid = meta['xid']
    except:
        xid = ipfs.cat(cid + '/xid').decode().strip()
        xid = str(uuid.UUID(xid))
        
    print('xid', xid)
    return xid

def authorize(filename):
    if filename[:2] == "Qm":
        cid = filename
    else:
        res = ipfs.add(filename)
        print('res', res)
        cid = res['Hash']

    xid = getXid(cid)

    # validate xid

    if xid in db:
        print('found xid', xid)

        last = db[xid]
        print('last', last)

        if cid == last['meta']:
            print("error, already submitted")
            return

        ownertx = last['auth']
        print('ownertx', ownertx)

        prev = [ ownertx ]
    else:
        print('first version of', xid)
        prev = []

    #scheme = binascii.hexlify(str.encode("CID1")).decode()
    
    cid = make_cid(cid)
    hexdata = cid.multihash.hex()
    #hexdata = binascii.hexlify(cid.to_v1().buffer).decode()
    #hexdata = scheme + cid1

    print('cid', hexdata)
    nulldata = { "data": hexdata }

    addr = blockchain.getnewaddress("auth", "bech32")
    print('addr', addr)
    authtxn = { addr: magic }

    rawtxn = blockchain.createrawtransaction(prev, [authtxn, nulldata])
    print('raw', rawtxn)

    funtxn = blockchain.fundrawtransaction(rawtxn)
    print('fun', funtxn)

    sigtxn = blockchain.signrawtransactionwithwallet(funtxn['hex'])
    print('sig', sigtxn)

    dectxn = blockchain.decoderawtransaction(sigtxn['hex'])
    print('dec', dectxn)

    acctxn = blockchain.testmempoolaccept([sigtxn['hex']])[0]
    print('acc', acctxn)

    if acctxn['allowed']:
        txid = blockchain.sendrawtransaction(sigtxn['hex'])
        print('txid', txid)
        writeWallet(xid, cid, dectxn)

def main():
    for arg in sys.argv[1:]:
        authorize(arg)

if __name__ == "__main__":
    # execute only if run as a script
    #main()
    authorize('QmSWCMGhWLbLEWKZst3x1f5QrqiPfbMsu1hKszadDrKcSt')
