"""
       Creates automated Emailer with error messages
            """
import logging
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage


class Email:

    def __init__(self, currentConfig):
        self.currentConfig = currentConfig
        self.error_data = []
        self.error_data_last = ""
        self.msg = EmailMessage()
        self.email_sent = False
        self.email_fail_count = 0
        self.email_sent_time = 0
        self.time_delta = 5
        self.time_remaining = 0
        self.build_msg = ""
        self.delay_time = int(self.currentConfig.config["EMAIL_SETTINGS"]["time_delay"])
        self.mail_host = self.currentConfig.config["EMAIL_SETTINGS"]["mail_host"]
        self.mail_port = self.currentConfig.config["EMAIL_SETTINGS"]["mail_port"]
        self.msg['Subject'] = self.currentConfig.config["EMAIL_SETTINGS"]["subject_line"]
        self.msg['From'] = self.currentConfig.config["EMAIL_SETTINGS"]["from"]
        self.msg['To'] = self.currentConfig.config["EMAIL_SETTINGS"]["to"]

    def SendEmail(self, Error):
        self.error_data = Error
        """  Creates a time stamp each time method is called 
             Once email is sent a
             To prevent emails being sent repeatedly a second time stamp is created (email_sent_time)
             to calculate a time delta from. If the problem still exists and the time delta is greater then 30 mins 
             a new email is sent."""
        self.time_delta = (time.time() - self.email_sent_time)

        if self.time_delta <= self.delay_time or self.error_data[-1] == self.error_data_last:
            self.time_remaining = self.delay_time - self.time_delta
            return
        else:
            """ This function Iterates Through the list of errors
                                    and converts them to a concatenated string.  """
            self.email_sent_time = time.time()
            logging.info(f'{self.error_data[-1]} ')

            if self.email_fail_count >= 5:
                logging.error(f'After {self.email_fail_count} attempts, Email failed. Skipping')

            for x in self.error_data:
                if x:
                    timestamp = datetime.now()
                    while x not in self.build_msg:
                        self.build_msg = self.build_msg + x + '\r\n '
                        self.msg.set_content(str(self.build_msg) + str(timestamp))

            try:
                timestamp = datetime.now()
                smtp_obj = smtplib.SMTP(self.mail_host, self.mail_port)
                smtp_obj.send_message(self.msg)
                log = f"Successfully sent email {timestamp}"
                self.email_fail_count = 0
                self.error_data.clear()
                self.build_msg = ""

            except smtplib.SMTPException:
                log = smtplib.SMTPException
                self.email_fail_count += 1
                print(log)
                return log
            else:
                self.error_data.clear()
                return log
