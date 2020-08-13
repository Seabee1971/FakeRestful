import logging
import os
import shutil
import smtplib
import time
import xml.etree.ElementTree as xml
from configparser import ConfigParser
from datetime import datetime
from email.message import EmailMessage

from pylogix import PLC

with PLC() as clx:
    class Data:
        """
         Class for loading PLC Data
         """

        def __init__(self, Config, Error):
            self.error = Error
            clx.IPAddress = Config.config['DEFAULT']['ip_address']
            self.ip_address = clx.IPAddress
            self.raw_header = ""
            self.raw_wash_data = ""
            self.raw_alarms = ""
            self.arr_num = 0  # Array Index Number
            self.load_values_status = False

        def LoadValues(self):
            """ Attempting to Connect and Confirm Connection
                to Allen Bradley PLC  """
            self.load_values_status = False
            self.raw_header = ""
            self.raw_wash_data = ""
            self.raw_alarms = ""
            while not self.load_values_status:
                try:
                    hd_cnt = 0
                    al_cnt = 0
                    while hd_cnt <= 10:
                        hd_cnt += 1
                        self.raw_header = clx.Read("Program:PRINT.Print_Form_Header[0]", 25)
                        if (
                                self.raw_header.Status.startswith("Part")
                                or str(self.raw_header.Value) != "None"
                        ):
                            break
                    else:
                        self.error.append('Failed to Load Header Values')
                        hd_cnt = 0
                        return False

                    while al_cnt <= 10:
                        al_cnt += 1
                        self.raw_alarms = clx.Read("Print_Alarm_Message_Buffer[0]", 65)
                        if (
                                self.raw_alarms.Status.startswith("Part")
                                or str(self.raw_alarms.Value) != "None"
                        ):
                            break
                    else:
                        self.error.append('Failed to Load Alarm Values')
                        al_cnt = 0
                        return False

                except Exception as e:
                    self.error.append(f'{e.args[-1]} failure to Load PLC tag values')
                    self.load_values_status = False

                else:
                    for a in range(20):
                        try:
                            raw_data = clx.Read(f"Program:PRINT.Print_Wash_Steps_Data[{a}]."
                                                f"Wash_Steps[0]", 40)
                        except Exception as e:
                            logging.warning(f'Failed to Read Tag {e.args[-1]}')
                            self.load_values_status = False
                        else:
                            if raw_data.Value[0] != "":
                                for val in raw_data.Value:
                                    self.raw_wash_data += str(val)
                            self.load_values_status = True
                    return True


class Strip:
    """ Used to strip unnecessary escape codes
         from message"""

    def __init__(self, Error):
        self.data = []
        self.error = Error
        self.stripped_data = ""

    def ReturnString(self, data):
        self.stripped_data = ""
        self.data = data
        try:

            for tags in self.data:
                tag = tags.strip('\n').strip('\n').strip('\r').strip()
                if (
                        tag
                        and not tag.startswith('VENTANA')
                        and not tag.startswith('---')
                        and not tag.endswith(':')
                ):
                    self.stripped_data = self.stripped_data + tag + "\t"
            assert isinstance(self.stripped_data, str), "Not a String"
        except Exception as e:
            logging.warning(f'Failed to Read Tag {e.args[-1]}')
            self.error.append(f'Failed to Read Tag {e.args[-1]}')
            if e.args[-1] == "Not a String":
                self.ReturnString(self.data)
            return self.error
        else:

            return self.stripped_data


class TransferFiles:
    def __init__(self, Config, Xml, Thread, Error):

        self.error = Error
        self.xml = Xml
        self.file_in_outbound = False
        self.file_in_EtQ = False
        self.fileName = None
        self.thread = Thread
        self.error_count = 0
        self.EtQ_folder = Config.config['FOLDER_LOCATIONS']['etq_folder']
        self.archive_folder = Config.config['FOLDER_LOCATIONS']['archive_folder']
        self.outbound_folder = Config.config['FOLDER_LOCATIONS']['outbound_folder']
        self.http_client = Config.config['RESTFUL_PARAMS']['http_client']
        self.get_request = Config.config['RESTFUL_PARAMS']['get_request']
        self.payload = Config.config['RESTFUL_PARAMS']['payload']
        self.header_auth = Config.config['RESTFUL_PARAMS']['header_auth']
        self.header_basic = Config.config['RESTFUL_PARAMS']['header_basic']
        self.headers = {self.header_auth: self.header_basic}
        self.conn = object
        self.RESTful_success = False
        self.err_cnt = 0
        self.x = None
        self.res = None
        self.data = None

    def OutboundFolder(self, filename):
        """Copies current file in the current Archive folder to outbound Folder.
                  """
        self.fileName = filename
        try:
            shutil.copy(self.fileName, self.outbound_folder)
        except Exception as e:
            self.error.append(f'Transfer to Outbound Failed{e.args[-1]}')
            self.file_in_outbound = False

        else:
            self.thread.init_new_receipt = False
            os.chdir(self.outbound_folder)
            if os.path.isfile(self.fileName):
                logging.info(f'{self.fileName} Transferred to outbound folder')
                self.file_in_outbound = True

    def EtQfolder(self):
        """Moves All files in the current outbound folder to EtQ Folder.
            This will attempt to transfer files that were
            missed early"""
        # if self.thread.EtQ_folder_exists and not self.file_in_EtQ:
        #     # x = 0
        for self.x, self.file in enumerate(os.listdir(self.outbound_folder), 1):
            if not os.path.exists(f'{self.EtQ_folder}/{self.file}'):
                try:
                    shutil.move(f'{self.outbound_folder}/{self.file}', self.EtQ_folder)
                except Exception as e:
                    self.error.append(f'Error Transferring {self.file} to ETQ {e.args[-1]}')
                    self.error.append('Transfer Failed')
                    self.error_count = self.error_count + 1
                else:
                    if os.path.isfile(f'{self.EtQ_folder}/{self.file}'):
                        logging.info(f'Moved {self.file} to {self.EtQ_folder}')

            else:
                logging.info(f'{self.file} already exists in {self.EtQ_folder}. Removing Duplicate file')
                os.remove(f'{self.outbound_folder}/{self.file}')
                if not os.path.exists(f'{self.outbound_folder}/{self.file}'):
                    logging.info(f'{self.file} has been removed from {self.outbound_folder}')
                    self.fileName = self.file
                    self.file_in_EtQ = True
            #  Confirming that the outbound folder is empty and the latest receipt is in EtQ folder.
            if not os.listdir(self.outbound_folder) and os.path.isfile(f'{self.EtQ_folder}/{self.fileName}'):
                logging.info(f'Moved {self.x} file(s) from {self.outbound_folder} to {self.EtQ_folder}')
                os.chdir(self.archive_folder)
                self.thread.init_new_receipt = False
                self.fileName = self.file
                self.file_in_EtQ = True

            else:
                self.file_in_EtQ = False

    def RESTfulCall(self):
        """Sends a RESTful Get request That notifies EtQ
            that a new receipt has been created and is ready
            to be uploaded into EtQ"""
        self.RESTful_success = True

        # while not self.RESTful_success and self.err_cnt <= 20:
        #     try:
        #         logging.info(f'Notifying EtQ that {self.fileName} is available')
        #         self.conn = http.client.HTTPSConnection(self.http_client)
        #         self.conn.request("GET", self.get_request, self.payload, self.headers)
        #         sleep(1)
        #         self.res = self.conn.getresponse()
        #         self.data = self.res.read()
        #     except Exception as e:
        #         self.error.append(f'Error in RESTful request {e.args[-1]}')
        #         self.err_cnt += 1
        #         self.RESTful_success = False
        #
        #     else:
        #
        #         EtQ_folder_after = os.listdir(self.EtQ_folder)
        #         if (self.res.status == 200 and "Operation done successfully" in self.data.decode('utf-8')) \
        #                 and len(EtQ_folder_after) == 0:
        #             self.error.clear()
        #             self.error.append("Operation done successfully")
        #             self.error.append(f'EtQ Server Response: {self.res.reason} Status: {self.res.status}')
        #             self.RESTful_success = True
        #
        #         else:
        #             sleep(1)
        #             self.err_cnt += 1
        #             logging.debug(f'RestFul Error Count = {self.err_cnt}')
        #             if self.err_cnt >= 20:
        #                 self.error.append(f'Status: {self.res.status} Attempts {self.err_cnt}')
        #             print(self.error)
        #             self.RESTful_success = False
        # else:
        #     self.err_cnt = 0
        #     sleep(10)
        #     self.RESTful_success = False


class CIPConfig:
    """
            This function loads the file "CIP_Gateway.ini"
            """

    def __init__(self):
        self.loadFeedback = None
        self.config = ConfigParser()

        try:
            self.config.read('CIP_gateway.ini')
        except Exception as e:
            print(f'{e} failed')
            self.load_failed()
        else:
            self.load_success()

    def load_success(self):
        self.loadFeedback = "Loaded Successful"
        return self.loadFeedback

    def load_failed(self):
        print(self)
        return "Failed"


class create_folder:
    def __init__(self, folderName):
        self.folderName = folderName
        logging.info(f'{self.folderName} does not exist. Creating Now')
        os.mkdir(self.folderName)
        # logging.info(os.path.exists(self.folderName))
        if os.path.exists(self.folderName):
            logging.info(f'{self.folderName} Created')
            os.chdir(self.folderName)
            logging.info(f'Current Folder: {os.getcwd()}')


class CreateXml:
    def __init__(self, plc, Config, Thread, Error):
        self.CurrentReceiptSaved = False
        self.error = Error
        self.id_time = None
        self.error_counter = 0
        self.config = Config
        self.EtQ_folder = Config.config['FOLDER_LOCATIONS']['etq_folder']
        self.working_folder = Config.config['FOLDER_LOCATIONS']['local_folder']
        self.archive_folder = Config.config['FOLDER_LOCATIONS']['archive_folder']
        self.outbound_folder = Config.config['FOLDER_LOCATIONS']['outbound_folder']
        self.fileName = None
        self.strip_split_header = ""
        self.PLC = plc
        self.thread = Thread
        self.root = xml.Element("CIPReceipt")  # Node
        self.ID = xml.SubElement(self.root, "ID")
        self.tree = xml.ElementTree(self.root)
        self.Date = xml.SubElement(self.root, "Date")
        self.Recipe = xml.SubElement(self.root, "Recipe")
        self.StartCycle = xml.SubElement(self.root, "CycleStart")
        self.StopCycle = xml.SubElement(self.root, "CycleStop")
        self.CycleAborted = xml.SubElement(self.root, "CycleAborted")
        self.Alarms = xml.SubElement(self.root, "Alarms")
        self.Data = xml.SubElement(self.root, "Data")

    def BuildFile(self, header, alarm, data):
        timestamp = datetime.now()
        self.id_time = timestamp.strftime('%Y%m%d%H%M%S')
        self.fileName = f'CIPReceipt_{self.id_time}.xml'
        try:
            strip_split_header = header.split('\t')
        except Exception as e:
            logging.warning(e.args[-1])
            raise Exception('')

        else:
            self.ID.text = self.id_time
            self.Date.text = strip_split_header[0]
            self.Recipe.text = strip_split_header[1]
            self.StartCycle.text = strip_split_header[2]
            self.StopCycle.text = strip_split_header[3]
            self.CycleAborted.text = strip_split_header[4]
            self.Alarms.text = str(alarm)
            self.Data.text = str(data)

    def SaveFile(self):
        if not os.path.exists(self.archive_folder):
            create_folder(self.archive_folder)
        if not self.CurrentReceiptSaved:
            try:
                logging.info(f'Changing to Archive Folder {self.archive_folder}')
                os.chdir(self.archive_folder)
            except Exception as e:
                self.error.append(f'Exception Catch {e.args[1]}')
                raise Exception(self.error)
            else:
                logging.info(f'Saving {self.fileName} in {self.archive_folder}')
                with open(self.fileName, "wb") as files:
                    self.tree.write(files)
                    if os.path.exists(self.fileName):
                        logging.info(f'({self.fileName}) was successfully saved in folder: {os.getcwd()}')
                    else:
                        self.error.append('Write Failed')
                        self.error.append(f'Unable to Write {self.fileName} to {self.outbound_folder} '
                                          f'Max Attempts Reached: {self.error_counter}')
                        raise Exception(self.error)
                    self.CurrentReceiptSaved = True

class Email:

    def __init__(self, currentConfig):
        self.currentConfig = currentConfig
        self.error_data = []
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

        if self.time_delta <= self.delay_time:
            self.time_remaining = self.delay_time - self.time_delta
            return
        else:
            """ This function Iterates Through the list of errors
                                    and converts them to a concatenated string.  """
            self.email_sent_time = time.time()
            logging.info(f'{self.error_data[-1]} ')

            if self.email_fail_count <= 5:
                self.email_fail_count = self.email_fail_count + 1
            else:
                logging.error(f'After {self.email_fail_count} attempts Email failed. Skipping')
            if type(self.error_data) != str:
                for x in self.error_data:
                    if x:
                        timestamp = datetime.now()
                        while x not in self.build_msg:
                            self.build_msg = self.build_msg + x + '\r\n '
                            self.msg.set_content(str(self.build_msg) + str(timestamp))
            else:
                self.msg.set_content(str(self.build_msg) + self.error_data)

            try:
                timestamp = datetime.now()
                smtp_obj = smtplib.SMTP(self.mail_host, self.mail_port)
                smtp_obj.send_message(self.msg)
                log = f"Successfully sent email {timestamp}"
                self.email_fail_count = 0
                if (type(self.error_data)) != str:
                    self.error_data.clear()
                self.build_msg = ""

            except smtplib.SMTPException:
                log = smtplib.SMTPException
                print(log)
                return log
            else:
                self.error_data.clear()
                return log
