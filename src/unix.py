# -*- coding:utf-8 mode:python -*-
'''
Created on 2014/09/07

@author: shimarin
'''

import logging,pwd,grp,getpass
import sudo

logger = logging.getLogger(__name__)
running_users_primary_gid = pwd.getpwnam(getpass.getuser()).pw_gid

class OperationFail(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class Reserved(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class InvalidName(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class AlreadyExists(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class UserDoesNotExist(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class GroupDoesNotExist(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class AlreadyMember(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

class NotMember(OperationFail):
    def __init__(self, msg = None):
        OperationFail.__init__(self, msg)

def ensure_str(maybeunicode):
    return maybeunicode.encode("utf-8") if isinstance(maybeunicode, unicode) else maybeunicode

def is_valid_user(uid, gid):
    return uid >= 1000 and uid <= 65530 and gid == running_users_primary_gid

def is_valid_group(gid):
    return gid >= 1000 and gid <= 65530

def user_exists(username):
    try:
        get_user(username)
    except UserDoesNotExist:
        return False
    return True

def get_user(username):
    username = ensure_str(username).lower()
    try:
        user = pwd.getpwnam(username)
    except KeyError:
        raise UserDoesNotExist(username)
    if not is_valid_user(user.pw_uid, user.pw_gid): raise UserDoesNotExist()
    return user

def get_group(groupname):
    groupname = ensure_str(groupname).lower()
    try:
        group = grp.getgrnam(groupname)
    except KeyError:
        raise GroupDoesNotExist(groupname)
    if not is_valid_group(group.gr_gid): raise GroupDoesNotExist()
    #else
    return group

'''
ユーザー名がこのシステムによって使用可能なものかチェックし、使用不可であれば例外を送出する
'''
def check_username_availability(username):
    try:
        user = pwd.getpwnam(username)
    except KeyError:
        return  # 未使用の場合は使用可能とする
    if not is_valid_user(user.pw_uid, user.pw_gid): # このシステムによって作成されたユーザーでない場合は例外
        raise Reserved("username: %s" % username)

'''
グループ名がこのシステムによって使用可能なものかチェックし、使用不可であれば例外を送出する
'''
def check_groupname_availability(groupname):
    try:
        group = grp.getgrnam(groupname)
    except KeyError:
        return # 未使用の場合は使用可能とする
    if not is_valid_group(group.gr_gid):# このシステムによって作成されたグループでない場合は例外
        raise Reserved("groupname: %s" % groupname)

'''
sudo useraddコマンドを発行する。
Possible exceptions: Reserved, InvalidName, AlreadyExists
'''
def useradd(username):
    username = ensure_str(username).lower()
    check_username_availability(username)
    try:
        sudo.execute(["useradd", "-d", "/dev/null", "-g", "oscar", "-M", "-N", "-s", "/sbin/nologin", username])
    except sudo.CommandFail, e:
        if e.returncode == 3: raise InvalidName(username)
        elif e.returncode == 9: raise AlreadyExists(username)
        else: raise

'''
sudo userdelコマンドを発行する。
Possible exceptions: Reserved, UserDoesNotExist
'''
def userdel(username):
    username = ensure_str(username).lower()
    check_username_availability(username)
    try:
        sudo.execute(["userdel", username])
    except sudo.CommandFail, e:
        if e.returncode == 6: raise UserDoesNotExist(username)
        else: raise
'''
sudo groupaddコマンドを発行する。
Possible exceptions: Reserved, InvalidName, AlreadyExists
'''
def groupadd(groupname):
    groupname = ensure_str(groupname).lower()
    check_groupname_availability(groupname)
    try:
        sudo.execute(["groupadd", groupname])
    except sudo.CommandFail, e:
        if e.returncode == 3: raise InvalidName(groupname)
        elif e.returncode == 9: raise AlreadyExists(groupname)
        else: raise

'''
sudo groupdelコマンドを発行する
Possible exceptions: Reserved, GroupDoesNotExist
'''
def groupdel(groupname):
    groupname = ensure_str(groupname).lower()
    check_groupname_availability(groupname)
    try:
        sudo.execute(["groupdel", groupname])
    except sudo.CommandFail, e:
        if e.returncode == 6: raise GroupDoesNotExist(groupname)
        else: raise

'''
sudo groupmems --add コマンドを発行する
Possible exceptions: Reserved, AlreadyMember, UserDoesNotExist, GroupDoesNotExist
'''
def memberadd(groupname, username):
    groupname = ensure_str(groupname).lower()
    username = ensure_str(username).lower()
    check_username_availability(username)
    check_groupname_availability(groupname)
    try:
        sudo.execute(["groupmems", "-g", groupname, "--add", username])
    except sudo.CommandFail, e:
        if e.returncode == 7: raise AlreadyMember("group:%s, user:%s" % (groupname, username))
        elif e.returncode == 8: raise GroupDoesNotExist(groupname)
        elif e.returncode == 9: raise UserDoesNotExist(username)
        else: raise

'''
sudo groupmems --del コマンドを発行する
Possible exceptions: Reserved, NotMember, GroupDoesNotExist
'''
def memberdel(groupname, username):
    groupname = ensure_str(groupname).lower()
    username = ensure_str(username).lower()
    check_groupname_availability(groupname)
    try:
        sudo.execute(["groupmems", "-g", groupname, "--del", username])
    except sudo.CommandFail, e:
        if e.returncode == 6: raise NotMember("group:%s, user:%s" % (groupname, username))
        elif e.returncode == 9: raise GroupDoesNotExist(groupname)
        else: raise

def users():
    return map(lambda x:x.pw_name, filter(lambda x:is_valid_user(x.pw_uid, x.pw_gid), pwd.getpwall()))

def groups():
    return map(lambda x:x.gr_name, filter(lambda x:is_valid_group(x.gr_gid), grp.getgrall()))

'''
Possible exceptions: GroupDoesNotExist
'''
def members(groupname):
    groupname = ensure_str(groupname).lower()
    group = get_group(groupname)
    return map(lambda x:x.pw_name, filter(lambda x:is_valid_user(x.pw_uid, x.pw_gid) and x.pw_uid in group.gr_mem, pwd.getpwall()))

'''
ユーザーがグループのメンバーかどうかを返す
'''
def ismember(groupname, username):
    user = get_user(username)
    group = get_group(groupname)
    return user.pw_uid in group.gr_mem

if __name__ == "__main__":
    logging.basicConfig()
    print users(), groups()
