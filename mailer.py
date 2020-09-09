"""Creates automated Emailer with error messages
            """
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage


class Email:

    def __init__(self, Config, EL):
        # self.currentConfig = Config
        self.el = EL
        self.error_data = []
        self.msg = EmailMessage()
        self.email_sent = False
        self.email_fail_count = 0
        self.email_sent_time = 0
        self.time_delta = 5
        self.time_remaining = 0
        self.build_msg = ""
        self.email_active = Config.email_active
        self.delay_time = Config.delay_time
        self.mail_host = Config.mail_host
        self.mail_port = Config.mail_port
        self.msg['Subject'] = Config.Subject
        self.msg['From'] = Config.From
        self.msg['To'] = Config.To

    def SendEmail(self, Error):
        self.error_data = Error
        if self.email_active:  # email_active is set in the CIP_gateway.ini file True = SendEmail to Group
            self.time_delta = (time.time() - self.email_sent_time)
            if self.time_delta <= self.delay_time:
                self.time_remaining = self.delay_time - self.time_delta
                return
            else:
                """ This function Iterates Through the list of errors
                                        and converts them to a concatenated string.  """
                self.email_sent_time = time.time()
                self.el.logger.info(f'{self.error_data[-1]} ')

                if self.email_fail_count >= 5:
                    self.el.logger.error(f'After {self.email_fail_count} attempts, Email failed. Skipping')

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
        else:
            self.el.logger.info(f'{self.error_data[-1]} ')
            self.error_data.clear()
            log = f'Email option is turned off in CIP_gateway.ini file'
            return log
