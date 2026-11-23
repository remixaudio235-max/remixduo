"""Bounded executor teardown; never block Qt shutdown indefinitely."""
import time

def bounded_shutdown(pool,timeout=.25):
    if pool is None:return
    pool.shutdown(wait=False,cancel_futures=True)
    deadline=time.monotonic()+max(0.,float(timeout))
    for thread in tuple(getattr(pool,"_threads",())):
        remaining=deadline-time.monotonic()
        if remaining<=0:break
        thread.join(remaining)

