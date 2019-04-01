import urllib.request
import logging
import threading
import argparse
import time
import datetime as dt


__version__ = 0.1
__author__ = 'Mishioo'


class RepeatingThread(threading.Thread):
    """Thread, that requests given site repetitively, with given interval,
    until any of the end conditions is met. End conditions might be one of:
    maximum number of calls, maximum time of running or certain moment in time.
    It can be stopped forcibly by calling repeating_thread.stopped.set()

    Parameters
    ----------
    address: str
        address of the desired site
    interval: float
        interval between each calls
    start_time: datetime.datetime, optional
        when to start execution, defaults to now
    finish_time: datetime.datetime, optional
        when to stop execution, defaults to start_time day at midnight
    max_number: int, optional
        how many calls to make, defaults to infinity
    max_time: datetime.timedelta, optional
        after how much time to stop, overrides finish_time if given
    event: threading.Event, optional
        event managing stopping thread's execution, if not given, new
        threading.Event is created"""
    def __init__(
            self, address, interval, start_time=dt.datetime.now(),
            finish_time=None, max_time=None,
            max_number=float('inf'), event=None, name=None, *, daemon=None
    ):
        super().__init__(name=name, daemon=daemon)
        self.interval = interval
        self.max_number = max_number
        self.start_time = start_time
        if max_time:
            self.finish_time = start_time + max_time
        else:
            self.finish_time = finish_time if finish_time else \
                start_time.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + dt.timedelta(days=1)
        if self.finish_time < self.start_time:
            raise ValueError(
                f'Finish time ({self.finish_time}) cannot be before the '
                f'start time ({self.start_time}).'
            )
        else:
            logging.info(f'Finish time set to {self.finish_time}.')
        self.address = address
        self.stopped = event if event else threading.Event()
        self.number = 0
        self.successes = 0
        self.threads_alive = 0

    def run(self):
        while not self.stopped and not dt.datetime.now() >= self.start_time:
            time.sleep(1)
        while not (
                dt.datetime.now() >= self.finish_time
                or self.number >= self.max_number
                or self.stopped.wait(self.interval)
        ):
            self.number += 1
            thread = threading.Thread(
                target=request_address,
                args=(self.address, self.number, self)
            )
            thread.start()
        while self.threads_alive:
            time.sleep(0.1)
        curr_time = dt.datetime.now()
        if self.number:
            logging.info(
                f'Made {self.successes} successful requests out of '
                f'total {self.number}.'
            )
        if self.start_time < curr_time:
            logging.info(f'Time taken: {curr_time-self.start_time}')
        logging.info(f'Exiting littlebot.')
        self.stopped.set()


def request_address(address, number, master):
    master.threads_alive += 1
    request = urllib.request.Request(
        address, headers={'User-Agent': 'Mozilla/5.0'}
    )
    try:
        req = urllib.request.urlopen(request)
    except Exception as e:
        logging.warning(f'Request no. {number}: failed due to error: {e}.')
        master.threads_alive -= 1
        return
    if not req.status == 200:
        logging.warning(
            f'Request no. {number}: failed with status: {req.status}.'
        )
    else:
        master.successes += 1
        logging.info(f'Request no. {number}: SUCCESS.')
    master.threads_alive -= 1


def repeat_request(
        address, interval, start_time, finish_time, max_time, max_number
):
    request = urllib.request.Request(
        address, headers={'User-Agent': 'Mozilla/5.0'}
    )
    try:
        req = urllib.request.urlopen(request)
    except Exception as e:
        logging.error(f'Initial request failed due to error: {e}')
        answer = input(
            'Would you like to (T)ry again, (C)ontinue anyway or (A)bort?'
        ).lower()
        while not answer.startswith(('t', 'c', 'a')):
            answer = input(
                f'Did not understand: "{answer}". '
                f'Would you like to (T)ry again, (C)ontinue anyway or (A)bort?'
            )
        if answer.startswith('c'):
            logging.info("Continuing initialization. Let's bot!")
            req = None
        elif answer.startswith('a'):
            logging.warning("Aborting littlebot initialization.")
            return
        else:
            return repeat_request(
                address, interval, start_time, finish_time, max_time, max_number
            )
    if not req:
        pass
    elif not req.status == 200:
        logging.warning(f'Initial request failed with status {req.status}')
        answer = input('Do you wish to continue anyway (Y/N)?').lower()
        while not answer.startswith(('y', 'n')):
            answer = input(
                f'Did not understand: "{answer}". '
                f'Do you wish to continue (Y/N)?'
            ).lower()
        if answer.startswith('y'):
            logging.info("Continuing initialization. Let's bot!")
        else:
            return
    else:
        logging.info("Initial request succeeded. Let's bot!")
    stop = threading.Event()
    littlebot = RepeatingThread(
        address, interval, start_time, finish_time, max_time, max_number, stop
    )
    littlebot.start()
    return littlebot


def get_arg_parser():
    parser = argparse.ArgumentParser(
        description='Request site repetitively with a given time interval, '
                    'until timeout or maximum number of requests exceeded.'
    )
    parser.add_argument(
        '-a', '--address', default=r'https://www.google.com/search?q=bing',
        help=r'Site address, defaults to "https://www.google.com/search?q=bing"'
    )
    parser.add_argument(
        '-i', '--interval', type=float, default=1.0,
        help='Interval between requests in seconds, defaults to 1'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true'
    )
    parser.add_argument(
        '-n', '--max_number', type=float, default=float('inf'),
        help='Maximum number of requests, defaults to inf'
    )
    parser.add_argument(
        '-t', '--max_time', type=lambda x: dt.timedelta(seconds=int(x)),
        help='Maximum time of running in seconds, defaults to 86400 (24h)'
    )
    parser.add_argument(
        '-s', '--start_time',
        type=lambda t: dt.datetime.strptime(t, '%m:%d:%H:%M'),
        default=dt.datetime.now(),
        help='When to start littlebot execution, in format "%%m:%%d:%%H:%%M" '
             '(month, day, hour, minute), current year assumed, defaults to now'
    )
    parser.add_argument(
        '-f', '--finish_time',
        type=lambda t: dt.datetime.strptime(t, '%m:%d:%H:%M'),
        help='When littlebot should be terminated, in format "%%m:%%d:%%H:%%M" '
             '(month, day, hour, minute), current year assumed, defaults to '
             'today at midnight'
    )
    return parser


if __name__ == '__main__':
    parser = get_arg_parser()
    args = parser.parse_args()
    logging.basicConfig(
        format='%(message)s',
        level=logging.INFO if args.verbose else logging.WARNING
    )
    logging.info(f'This is littlebot v.{__version__} by {__author__}.')
    today = dt.datetime.today()
    finish_time = None if not args.finish_time else dt.datetime(
        today.year, args.finish_time.month, args.finish_time.day,
        args.finish_time.hour, args.finish_time.minute
    )
    littlebot = repeat_request(
        args.address, args.interval, args.start_time, finish_time,
        args.max_time, args.max_number
    )
    logging.info('To force exit press Ctrl+C')
    try:
        while not littlebot.stopped.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        logging.warning(f'Will exit after at most {args.interval} seconds.')
        littlebot.stopped.set()
    except AttributeError:
        logging.warning("Initialization failed. Exiting littlebot.")
