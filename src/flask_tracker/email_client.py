
# coding: utf-8

# pylint: disable=missing-docstring
# pylint: disable=logging-format-interpolation
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=broad-except

import asyncio
import smtplib
import imaplib
import time
import ssl
import logging
import socket
import traceback

# ~ from email import message_from_string
import email.mime.application
import email.mime.multipart
import email.mime.text


def set_logging(log_level):
    fmt_ = logging.Formatter('[%(asctime)s]'
                             '%(name)s:'
                             '%(levelname)s:'
                             '%(funcName)s() '
                             '%(filename)s:'
                             '%(lineno)d: '
                             '%(message)s ')

    ch = logging.StreamHandler()
    ch.setFormatter(fmt_)
    logger_ = logging.getLogger()
    logger_.handlers = []
    logger_.addHandler(ch)
    logger_.setLevel(log_level)


class EMailClient(object):    # pylint: disable=too-many-instance-attributes

    user = None
    password = None
    machie_id = None

    def __init__(self,
                 path_to_credentials,
                 imap_host_port,
                 smtp_host_port,
                 time_step=60):

        self.path_to_credentials = path_to_credentials
        self.imap_host, self.imap_port = imap_host_port.split(':')
        self.smtp_host, self.smtp_port = smtp_host_port.split(':')
        self.time_step = time_step

        self.IMAPconnection = None
        self.last_email_check = 0

    def _load_credentials(self):

        logging.info("self.path_to_credentials:{}".format(self.path_to_credentials))
        with open(self.path_to_credentials) as src:
            for n, l in enumerate(list(src.readlines())):
                try:
                    if not isinstance(l, str):
                        l = l.decode()
                    l_ = l.strip()
                    toks = [i for i in l_.split() if i]
                    if toks and not toks[0].startswith('#'):
                        self.user, self.password = l_.split()
                except Exception as exc:
                    logging.error("{}:{} exc:{}".format(self.path_to_credentials, n, exc))

    def _handle_email_message(self, email_from, email_body):

        # ~ logging.warning("email_from({}):{}".format(type(email_from), email_from))
        # ~ logging.warning("email_body({}):{}".format(type(email_body), email_body))

        sender = ''
        for i in email_from:
            toks = str(i).split('From: ')
            if toks[1:]:
                sender = toks[1].split('\\r')[0]
                break

        # ~ for i in email_body:
            # ~ s_body = str(i)

        logging.warning("sender:{}".format(sender))
        for i, b in enumerate(email_body):
            if isinstance(b, str):
                logging.warning("email_body[{}]:{}".format(i, b))
            else:
                for j, k in enumerate(b):
                    toks = str(k).split('\\r\\n\\r\\n')
                    logging.warning("email_body[{}][{}]:{}".format(i, j, toks))

    def connect(self):

        self._load_credentials()
        self.IMAPconnection = imaplib.IMAP4_SSL(self.imap_host, int(self.imap_port))
        self.IMAPconnection.login(self.user, self.password)

    def _receive(self):

        if self.IMAPconnection:
            self.IMAPconnection.select('INBOX')
            res, data = self.IMAPconnection.uid('search', None, '(UNSEEN)')
            uid_list = data[0].split()

            if data[0]:
                logging.warning("res:{}, data :{}".format(res, data))

            for uid_ in uid_list[:1]:
                result, email_from = self.IMAPconnection.uid('fetch', uid_, "(BODY[HEADER.FIELDS (FROM)])")
                if result != 'OK':
                    logging.error("result:{}".format(result))
                result, email_body = self.IMAPconnection.uid('fetch', uid_, '(UID BODY[TEXT])')
                if result != 'OK':
                    logging.error("result:{}".format(result))

                self._handle_email_message(email_from, email_body)

    def send(self, dest, msg_subject, msg_body=None, attach_stream=None, attach_type=None, attach_filename=None):  # pylint: disable=too-many-arguments

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(self.smtp_host, int(self.smtp_port), context=context) as conn:

            conn.ehlo()

            self._load_credentials()
            conn.login(self.user, self.password)

            msg = email.mime.multipart.MIMEMultipart()
            msg['To'] = dest
            msg['Subject'] = msg_subject
            # ~ msg['From'] = self.user
            msg['From'] = "FlaskTrack"

            if msg_body:
                body = email.mime.text.MIMEText(msg_body)
                msg.attach(body)

            if attach_stream:
                att = email.mime.application.MIMEApplication(attach_stream, _subtype=attach_type)
                att.add_header('Content-Disposition', 'attachment', filename=attach_filename)
                msg.attach(att)

                msg.attach(att)

            ret = conn.send_message(msg)
            logging.warning("ret:{}".format(ret))

    def close(self):

        if self.IMAPconnection:
            self.IMAPconnection.close()

    def poll(self):

        if self.time_step > 0 and time.time() - self.last_email_check > self.time_step:
            self.last_email_check = time.time()
            try:

                self.connect()
                self._receive()
                self.close()

            except socket.gaierror as exc:
                logging.info(exc)
            except Exception as exc:
                logging.error(exc)
                logging.debug(traceback.format_exc())

            dt = time.time() - self.last_email_check
            if dt > 1:
                logging.warning("dt:{}".format(dt))

    async def receive_loop(self):

        while True:
            self.poll()
            await asyncio.sleep(self.time_step)
