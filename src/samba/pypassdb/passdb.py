# -*- coding: utf-8 -*-
import tdb
from user import unpack_user
from struct import unpack, pack

USER_PREFIX = "USER_"
NEXT_RID_KEY = "NEXT_RID\x00"


def userkey(user):
    return USER_PREFIX+user+"\x00"


class PassDB:
    def __init__(self, name, hash_size=0):
        self.db = tdb.open(name, hash_size)

    def __contains__(self, name):
        return self.db.get(userkey(name)) is not None

    def __getitem__(self, name):
        return unpack_user(self.db[userkey(name)])

    def __setitem__(self, name, user):
        assert name == user.username
        self.db[userkey(name)] = user.pack()

    def __delitem__(self, name):
        self.db.transaction_start()
        rid = self[name].user_rid
        del self.db[userkey(name)]
        del self.db["RID_%08x\x00" % rid]
        self.db.transaction_commit()

    def __iter__(self):
        for x in self.db:
            if x.startswith("USER_"):
                yield unpack_user(self.db[x])

    def append(self, user):
        self.db.transaction_start()
        if user.user_rid is None:
            (rid,) = unpack("<I", self.db[NEXT_RID_KEY])
            user.user_rid = rid
            self.db[NEXT_RID_KEY] = pack("<I", rid+1)
        self.db[userkey(user.username)] = user.pack()
        self.db["RID_%08x\x00" % user.user_rid] = user.username+"\x00"
        self.db.transaction_commit()

    def close(self):
        self.db.close()

class PassDBContext:
    def __init__(self, name, hash_size=0):
        self.name = name
        self.hash_size = hash_size
    def __enter__(self):
        self.passdb = PassDB(self.name, self.hash_size)
        return self.passdb
    def __exit__(self,exc_type, exc_value, traceback):
        self.passdb.close()
        return exc_type is None

def passdb_open(name, hash_size=0):
    return PassDBContext(name, hash_size)
