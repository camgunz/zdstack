from __future__ import with_statement

###
# This isn't a traditional thread pool in the sense that there's X threads
# working on a Queue of tasks.  However, it is useful to keep track of all
# spawned threads so that they can be join()'d later.
###

"""

ZDSThreadPool is the module controlling threads in ZDStack.

Getting a thread is not completely straight-forward.  In ZDStack, all
custom threads run in loops with termination conditions.
'get_thread()' pulls those common patterns into itself, so that only
the internal logic needs to be provided as a function, and the looping
logic can be left to 'get_thread()'.

This means, however, that the provided function should not block
forever in any circumstance.  It needs to regularly timeout so that
'get_thread()' can check its termination condition and finish if that
condition is met.

In the same vein, running 'join()' on a thread doesn't instantly
terminate the thread, in fact, this will block until either the
thread's termination condition is met or DIE_THREADS_DIE is set.  Thus
it is critical that the provided function not block forever, indeed it
is best if the logic 'timeout' at least every second (preferably immediately)

Running 'join()' in a thread that isn't finished will block until its
termination condition is met, or DIE_THREADS_DIE is set.  This is all
contingent on the basic 'target' function timing out periodically so
the termination condition or DIE_THREADS_DIE can be checked.

"""

import time
import logging

from threading import Thread, Lock

from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT

__THREAD_POOL = []
__THREAD_POOL_LOCK = Lock()

def get_thread(target, name, keep_going, sleep=None):
    """Creates a thread.

    target:     a function to run continuously in a while loop.
    name:       a string representing the name to give to the new thread.
    keep_going: a function that returns a boolean.  if the boolean is
                false, the thread will stop running target().
    sleep:      an int/float/Decimal representing the amount of time
                to sleep between loop iterations.  Optional, defaults
                to not sleeping at all.

    """
    logging.debug("Getting thread %s" % (name))
    global __THREAD_POOL
    global __THREAD_POOL_LOCK
    with __THREAD_POOL_LOCK:
        def tf():
            while 1:
                if DIE_THREADS_DIE:
                    s = "[%s]: DIE_THREADS_DIE is set, quitting loop"
                    logging.debug(s % (name))
                    break
                elif not keep_going():
                    s = "[%s]: Termination condition is set, quitting loop"
                    logging.debug(s % (name))
                    break
                target()
                if sleep:
                    time.sleep(sleep)
            logging.debug("[%s]: I have quit my loop!" % (name))
        t = Thread(target=tf, name=name)
        logging.debug("Adding thread [%s]" % (t.getName()))
        __THREAD_POOL.append(t)
        s = "%d threads currently in thread pool"
        logging.debug(s % (len(__THREAD_POOL)))
        t.start()
        return t

def process_queue(input_queue, name, keep_going, output_queue=None, sleep=None):
    """Creates a thread that processes tasks in a Queue.

    target:       a function to run continuously in a while loop.
    name:         a string representing the name to give to the new
                  thread.
    keep_going:   a function that returns a boolean.  if the boolean is
                  false, the thread will stop running target().
    input_queue:  a queue from which to obtain tasks.
    output_queue: a queue in which to place task output.  Optional.
    sleep:        an int/float/Decimal representing the amount of time
                  to sleep between loop iterations.  Optional, defaults
                  to not sleeping at all.

    """
    def tf():
        while 1:
            if DIE_THREADS_DIE:
                s = "[%s]: DIE_THREADS_DIE is set, quitting loop"
                logging.debug(s % (name))
                break
            try:
                ###
                # If we're shutting down, this thread will wait forever on
                # a task that will never come.  So we want to check to see
                # if we're shutting down every MAX_TIMEOUT seconds.
                ###
                task = input_queue.get(block=True, timeout=MAX_TIMEOUT)
                output = task.perform()
                input_queue.task_done()
                if output and output_queue:
                    output_queue.put_nowait(output)
            except Queue.Empty:
                ###
                # If this thread has been stopped, its keep_going function
                # will return False.  Otherwise just try to get more tasks.
                ###
                if keep_going():
                    continue
                else:
                    ###
                    # OK, so we should quit.  This means something has
                    # .join()'d our Queue, and is waiting on us to perform
                    # all the tasks from it.  Since our Queue was just
                    # empty, this has apparently already done!
                    ###
                    s = "[%s]: No more tasks, quitting loop"
                    logging.debug(s % (name))
                    break
            except Exception, e:
                logging.error("[%s] received error: [%s]" % (name, e))
            if sleep:
                time.sleep(sleep)
        logging.debug("[%s]: I have quit my loop!" % (name))
    with __THREAD_POOL_LOCK:
        t = Thread(target=tf, name=name + ' Processing Thread')
        logging.debug("Adding thread [%s]" % (t.getName()))
        __THREAD_POOL.append(t)
        s = "%d threads currently in thread pool"
        logging.debug(s % (len(__THREAD_POOL)))
        t.start()
        return t

def join(thread, acquire_lock=True):
    """Joins a thread, removing it from the global pool.

    thread: a thread instance.
    acquire_lock: a boolean that, if given, will acquire the thread
                  pool lock before joining the thread.  True by
                  default.

    """
    global __THREAD_POOL
    global __THREAD_POOL_LOCK
    def blah():
        logging.debug("Joining thread [%s]" % (thread.getName()))
        thread.join()
        logging.debug("Removing thread [%s]" % (thread.getName()))
        try:
            __THREAD_POOL.remove(thread)
        except ValueError:
            logging.error("Thread [%s] not found in pool" % (thread.getName()))
    if acquire_lock:
        with __THREAD_POOL_LOCK:
            blah()
    else:
        blah()

def join_all():
    """Joins all threads."""
    logging.debug("Joining all threads")
    global __THREAD_POOL
    global __THREAD_POOL_LOCK
    with __THREAD_POOL_LOCK:
        for t in __THREAD_POOL:
            join(t, acquire_lock=False)

