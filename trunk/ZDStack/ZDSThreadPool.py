from __future__ import with_statement

###
# This isn't a traditional thread pool in the sense that there's X threads
# working on a Queue of tasks.  However, it is useful to keep track of all
# spawned threads so that they can be join()'d later.
###

"""

ZDSThreadPool is the module controlling threads in ZDStack.

ZDStack runs the following threads:

  - a Timer that checks that ZServ log links and FIFOs are created
  - a Timer that checks for crashed zservs and restarts them
  - a normal Thread that polls zserv FIFOs for output
  - 4 worker threads that perform Tasks from their Queues
    - output tasks
    - generic event tasks
    - command event tasks
    - plugin event tasks

Getting a Timer is easy, so there's no wrapper logic here for that.

For normal threads without Queues to work on, they need termination
conditions so they don't run forever.  They also need to check these
termination conditions every so often.  get_thread() handles all this.

For worker threads, we still want to be able to stop them -- but we
want all their Tasks to be performed first.  So while these threads
still have termination conditions, these conditions aren't "terminate
as soon as I say so", but "terminate when all your Tasks are
performed".  process_queue() handles all this.

I suppose I could go further and create a QueueProcessor that has
.join() methods and what-not, but that seems like over-engineering.

"""

import time
import Queue
import traceback

from threading import Thread, Lock

from ZDStack import DIE_THREADS_DIE, MAX_TIMEOUT, get_zdslog
from ZDStack.Utils import requires_lock

zdslog = get_zdslog()

__THREAD_POOL = list()
__THREAD_POOL_LOCK = Lock()

@requires_lock(__THREAD_POOL_LOCK)
def _add_thread(t):
    """Adds a thread to the thread pool.

    :param t: a thread to add to the thread pool
    :type t: threading.Thread

    """
    global __THREAD_POOL
    zdslog.debug("Adding thread [%s]" % (t.getName()))
    __THREAD_POOL.append(t)
    s = "%d threads currently in thread pool"
    zdslog.debug(s % (len(__THREAD_POOL)))

def get_thread(target, name, keep_going, sleep=None):
    """Creates a thread.

    :param target: a function to run continuously in a while loop.
    :type target: function
    :param name: the name to give to the new thread.
    :type name: string
    :param keep_going: a function that returns a boolean; if the
                       boolean is false, the thread will stop running
                       target().
    :type keep_going: function
    :param sleep: the amount of time to sleep between loop iterations;
                  optional, defaults to not sleeping at all
    :type sleep: int, float or Decimal
    :rtype: threading.Thread
    :returns: the newly created Thread

    """
    zdslog.debug("Getting thread %s" % (name))
    def tf():
        while 1:
            if DIE_THREADS_DIE:
                s = "[%s]: DIE_THREADS_DIE is set, quitting loop"
                zdslog.debug(s % (name))
                break
            elif not keep_going():
                s = "[%s]: Termination condition is set, quitting loop"
                zdslog.debug(s % (name))
                break
            target()
            if sleep:
                time.sleep(sleep)
        zdslog.debug("[%s]: I have quit my loop!" % (name))
    t = Thread(target=tf, name=name)
    _add_thread(t)
    t.start()
    return t

def process_queue(input_queue, name, keep_going, output_queue=None, sleep=None):
    """Creates a thread that processes tasks in a Queue.

    :param input_queue: the queue from which to obtain Tasks to perform
    :type input_queue: Queue.Queue
    :param name: the name to give to the new thread.
    :type name: string
    :param keep_going: a function that returns a boolean; if the
                       boolean is false, the thread will stop running
                       target().
    :type keep_going: function
    :param output_queue: optional, the queue into which the output of
                         the performed Tasks will be placed
    :type output_queue: Queue.Queue
    :param sleep: the amount of time to sleep between loop iterations;
                  optional, defaults to not sleeping at all
    :type sleep: int, float or Decimal
    :rtype: threading.Thread
    :returns: the newly created Thread

    """
    def tf():
        while 1:
            if DIE_THREADS_DIE:
                s = "[%s]: DIE_THREADS_DIE is set, quitting loop"
                zdslog.debug(s % (name))
                break
            if not keep_going():
                s = "[%s]: Quitting, %d tasks remaining in queue"
                zdslog.debug(s % (name, input_queue.qsize()))
            try:
                ###
                # If we're shutting down, this thread will wait forever on
                # a task that will never come.  So we want to check to see
                # if we're shutting down every MAX_TIMEOUT seconds.
                ###
                task = input_queue.get(block=True, timeout=MAX_TIMEOUT)
                task.perform(input_queue, output_queue)
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
                    # empty, this has apparently already been done!
                    ###
                    s = "[%s]: No more tasks, quitting loop"
                    zdslog.debug(s % (name))
                    break
            except Exception, e:
                es = "[%s] received error: [%s]\n%s"
                zdslog.error(es % (name, e, traceback.format_exc()))
            if sleep:
                time.sleep(sleep)
        zdslog.debug("[%s]: I have quit my loop!" % (name))
    t = Thread(target=tf, name=name + ' Processing Thread')
    _add_thread(t)
    t.start()
    return t

@requires_lock(__THREAD_POOL_LOCK)
def join(thread):
    """Joins a thread, removing it from the global pool.

    :param thread: the thread to join
    :type thread: threading.Thread

    """
    global __THREAD_POOL
    zdslog.debug("Joining thread [%s]" % (thread.getName()))
    thread.join()
    zdslog.debug("Removing thread [%s]" % (thread.getName()))
    try:
        __THREAD_POOL.remove(thread)
    except ValueError:
        zdslog.error("Thread [%s] not found in pool" % (thread.getName()))

@requires_lock(__THREAD_POOL_LOCK)
def join_all():
    """Joins all threads."""
    zdslog.debug("Joining all threads")
    global __THREAD_POOL
    for t in __THREAD_POOL:
        zdslog.debug("Thread Pool: %s" % ([x.getName() for x in __THREAD_POOL]))
        zdslog.debug("Joining [%s]" % (t.getName()))
        t.join()
        zdslog.debug("Joined [%s]" % (t.getName()))
    __THREAD_POOL = list()
    zdslog.debug("All threads joined")

