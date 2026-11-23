"""Compatibility entry for the real platform instance lease.

Windows mutex name stays byte-for-byte compatible with the native observer.
The caller keeps the lease alive; macOS uses a real advisory file lock.
"""
import _remix_bootstrap
_instances=[]

def acquire_instance():
    from remix_duo.platforms.factory import services
    from remix_duo.platforms.paths import app_paths
    lease=services().acquire_lock("RemiXSignalSmaartDataBarV823",app_paths().data)
    if lease is not None:
        _instances.append(lease)
    return lease
