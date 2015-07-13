import threading


class PoliteThread(threading.Thread):

    """A polite Thread that waits for other Threads to finish before
    starting.
    """

    def __init__(self, wait_for, **kwargs):
        super().__init__(**kwargs)
        try:
            self.wait_for = list(wait_for)
        except TypeError:
            self.wait_for = [wait_for]
        self.ran = False

    def run(self):
        for thread in self.wait_for:
            thread.join()
        self.ran = True
        super().run()


if __name__ == '__main__':
    import time
    import logging

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(threadName)s] %(message)s'
    )
    logger = logging.getLogger(__name__)

    def long_computation(duration):
        logger.info('Starting computation')
        time.sleep(duration)
        logger.info('Finish')

    t1 = threading.Thread(target=long_computation, args=(1,))
    t1.start()

    t2 = PoliteThread(wait_for=t1, target=long_computation, args=(1,))
    t2.start()

    t3 = PoliteThread(wait_for=[], target=long_computation, args=(1,))
    t3.start()

    t4 = PoliteThread(wait_for=(t1, t2), target=long_computation, args=(1,))
    t4.start()
