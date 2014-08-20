'''
Created on 2014/08/20

@author: shimarin
'''

import os

def get_capacity(path):
    st = os.statvfs(path)

    return {
        "free":st.f_bavail * st.f_frsize,
        "total":st.f_blocks * st.f_frsize,
        "used":(st.f_blocks - st.f_bfree) * st.f_frsize
    }

def capacity_string(nbytes):
    if nbytes >= 1024 * 1024 * 1024 * 1024:
        return "%.1fTB" % (nbytes / (1024 * 1024 * 1024 * 1024.0))
    if nbytes >= 1024 * 1024 * 1024:
        return "%.1fGB" % (nbytes / (1024 * 1024 * 1024.0))
    if nbytes >= 1024 * 1024:
        return "%.1fMB" % (nbytes / (1024 * 1024.0))
