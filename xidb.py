import ipfshttpclient
import uuid
import json
import zlib
import time
import os
import cid
import binascii

def getIpfs():
    connect = os.environ.get('IPFS_CONNECT')

    if connect:
        return ipfshttpclient.connect(connect)
    else:
        return ipfshttpclient.connect()

def checkIpfs():
    for i in range(10):
        try:
            ipfs = getIpfs()
            #print(ipfs.id())
            return True
        except:
            print(i, "attempting to connect to IPFS...")
            time.sleep(1)
    return False

def verifyXid(xid):
    try:
        u = uuid.UUID(xid)    
        z = zlib.compress(u.bytes)
        if len(z) > len(u.bytes):
            return str(u)
        else:
            print(f"invalid {xid} compresses to {len(z)}")
            return None
    except:
        return None

def getXid(cid):
    xid = None
    ipfs = getIpfs()

    try:
        meta = json.loads(ipfs.cat(cid))
        xid = meta['xid']
    except:
        try:
            meta = json.loads(ipfs.cat(cid + '/meta.json'))
            xid = meta['xid']
        except:
            try:
                # deprecated
                xid = ipfs.cat(cid + '/xid')
                xid = xid.decode().strip()
            except:
                print(f"error: unable to retrieve xid for {cid}")
        
    return verifyXid(xid)

def getMeta(cid):
    meta = None
    ipfs = getIpfs()

    try:
        meta = json.loads(ipfs.cat(cid))
    except:
        try:
            meta = json.loads(ipfs.cat(cid + '/meta.json'))
        except:
            pass

    return meta

def getVersions(cid):
    versions = []

    version = getCert(cid)
    version['auth_cid'] = cid

    while version:
        versions.append(version)
        print(version)
        prev = version['prev']
        if prev:
            version = getCert(prev)
            version['auth_cid'] = prev
        else:
            version = None

    versions.reverse()
    
    return versions

def getCert(cid):
    ipfs = getIpfs()
    return json.loads(ipfs.cat(cid))

def addCert(cert):
    ipfs = getIpfs()
    res = ipfs.add(cert)
    return res['Hash']

def encodeCid(hash):
    cid1 = cid.make_cid(hash)
    return binascii.hexlify(cid1.to_v1().buffer).decode()
