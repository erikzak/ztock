"""
Utility function for initiating logger. Will create a rotating log file
containing each days trading, with log files rotating at midnight.

If gmail credentials are supplied, sends errors by mail to list of recipients.

Also handles console output.
"""
import datetime
import logging
import smtplib
from logging.handlers import TimedRotatingFileHandler
from typing import List, Union

from .config import Config
from .constants import LOG_NAME, ORDER_LOG_NAME


LOG_FMT = "%(asctime)s %(name)s %(levelname)s - %(message)s"
ORDER_FMT = "%(asctime)s - %(message)s"
DATE_FMT = "%Y.%m.%d %H:%M:%S"
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


_CONFIG = None


def _set_log_config(config: Config) -> None:
    """Stores config object for later use."""
    global _CONFIG
    _CONFIG = config
    return


def get_log_config() -> Config:
    """Returns logging config object."""
    global _CONFIG
    return _CONFIG


class BufferingSMTPHandler(logging.handlers.BufferingHandler):
    """
    Custom SMTP handler to send all errors once, instead of individual mails
    per error.

    https://stackoverflow.com/questions/1610845/collate-output-in-python-logging-memoryhandler-with-smtphandler
    https://gist.github.com/anonymous/1379446
    """
    _last_mail = None

    def __init__(
            self,
            mailhost,
            mailport,
            fromaddr,
            toaddrs,
            subject,
            username: str,
            password: str,
            hours_between_mails: int = None,
            capacity: int = 1000
    ):
        logging.handlers.BufferingHandler.__init__(self, capacity)
        self.mailhost = mailhost
        self.mailport = mailport
        self.fromaddr = fromaddr
        self.toaddrs = toaddrs
        self.subject = subject
        self.username = username
        self.password = password
        self.hours_between_mails = hours_between_mails
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s"))
        return

    def flush(self):
        if (len(self.buffer) == 0):
            return
        logger = logging.getLogger(LOG_NAME)

        # Checks if errors have been logged, then if error mail should be sent
        # based on mail interval
        if (self._last_mail and self.hours_between_mails):
            hours_since_last_mail = (datetime.datetime.now() - self._last_mail).total_seconds() // 3600
            if (hours_since_last_mail < self.hours_between_mails):
                # Less than defined hours between mails, waiting with log flush
                logger.debug("Less than {} hour(s) ({}) since last error mail".format(
                    self.hours_between_mails, hours_since_last_mail
                ))
                return
            logger.debug("Hours since last error mail: {}, flushing buffer".format(
                hours_since_last_mail
            ))

        try:
            # Connect to SMTP server
            server = smtplib.SMTP(self.mailhost, self.mailport)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.username, self.password)
            # Create body
            body = ""
            for record in self.buffer:
                text = self.format(record)
                body += text + "\r\n"
            # Create message
            msg = "\r\n".join([
                f"From: {self.fromaddr}",
                f"To: {','.join(self.toaddrs)}",
                f"Subject: {self.subject}",
                "",
                f"{body}",
            ])
            # Send mail
            server.sendmail(self.fromaddr, self.toaddrs, msg)
            self._last_mail = datetime.datetime.now()
            self._errors_logged = False
            server.quit()
        except Exception:
            self.handleError(None)  # no particular record
        finally:
            # Try to log out on errors
            try:
                server.quit()
            except Exception:
                pass

        # Empty buffer
        self.buffer = []
        return


def init_log(config: Config) -> logging.Logger:
    """
    Inits logger based on config. The following attributes can be defined in
    the config object:

    * level (str): logging level to use. Defaults to INFO
    * file (str): optional path to use for log files, will create <file_path>
        and <file_path>.<timestamp> files on rotation
    * mail (dict): optional SMTP mail handler for sending log errors and order
        notifications by mail. The dictionary must contain these key-value pairs:
        * errors_to (str or list of str): mail address or list of addresses to
            send log errors to
        * orders_to (str or list of str): mail address or list of addresses to
            send order notifications to
        * smtp_host (str): SMTP mail server host name
        * smtp_port (int): SMTP mail server port
        * address (str): mail address used to send errors
        * username (str): mail account username
        * password (str): mail account password

    :param config: logging config object
    :type config: Config
    """
    _set_log_config(config)

    # Get logging level enum
    level_str = getattr(config, "level", "INFO")
    level = LEVEL_MAP[level_str.upper()]

    # Generate formatter and get logger
    formatter = logging.Formatter(LOG_FMT, DATE_FMT)
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    file_path = getattr(config, "file", None)
    if (file_path):
        file_handler = TimedRotatingFileHandler(file_path, when="midnight")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    mail_config = getattr(config, "mail", None)
    if (mail_config):
        # Error mail handler
        errors_to = mail_config.get("errors_to", None)
        if (errors_to):
            error_mail_handler = init_mail_handler(
                mail_config,
                recipients=errors_to,
                subject=f"{LOG_NAME} error",
                level=logging.ERROR,
                formatter=formatter,
                interval=mail_config.get("error_interval", None)
            )
            logger.addHandler(error_mail_handler)

        # Order mail handler
        orders_to = mail_config.get("orders_to", None)
        if (orders_to):
            order_formatter = logging.Formatter(ORDER_FMT, DATE_FMT)
            order_mail_handler = init_mail_handler(
                mail_config,
                recipients=orders_to,
                subject=ORDER_LOG_NAME,
                level=logging.INFO,
                formatter=order_formatter,
                interval=mail_config.get("order_interval", None)
            )
            order_logger = logging.getLogger(ORDER_LOG_NAME)
            order_logger.setLevel(logging.INFO)
            order_logger.addHandler(order_mail_handler)
    return logger


def init_mail_handler(
        mail_config: Config,
        recipients: Union[str, List[str]],
        subject: str,
        level: str,
        formatter: logging.Formatter,
        interval: int = 0
) -> BufferingSMTPHandler:
    """Returns a logging mail handler based on defined config."""
    if (isinstance(recipients, str)):
        recipients = [recipients]
    mail_handler = BufferingSMTPHandler(
        mailhost=mail_config.smtp_host,
        mailport=mail_config.smtp_port,
        fromaddr=mail_config.address,
        toaddrs=recipients,
        subject=subject,
        username=mail_config.username,
        password=mail_config.password,
        hours_between_mails=interval
    )
    mail_handler.setLevel(level)
    mail_handler.setFormatter(formatter)
    return mail_handler


def set_log_level(level: str = None) -> None:
    """Updates log level. Defaults to logging.INFO"""
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(LEVEL_MAP.get(level.upper(), "INFO"))
    return


def flush_log():
    """Tries to flush all log handlers to send error notifications by mail."""
    logger = logging.getLogger(LOG_NAME)
    order_logger = logging.getLogger(ORDER_LOG_NAME)

    # Flush log handlers
    logger.debug("Flushing log handlers")
    for log_handler in logger.handlers:
        try:
            log_handler.flush()
        except Exception as e:
            logger.warning("Unable to flush log handler: {}".format(e))

    # Send order mails
    for log_handler in order_logger.handlers:
        try:
            log_handler.flush()
        except Exception as e:
            logger.warning("Unable to flush order mail handler: {}".format(e))
    return
