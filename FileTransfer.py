import http.client
import logging
import os
import shutil
from time import sleep


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

        while not self.RESTful_success and self.err_cnt <= 20:
            try:
                logging.info(f'Notifying EtQ that {self.fileName} is available')
                self.conn = http.client.HTTPSConnection(self.http_client)
                self.conn.request("GET", self.get_request, self.payload, self.headers)
                sleep(1)
                self.res = self.conn.getresponse()
                self.data = self.res.read()
            except Exception as e:
                self.error.append(f'Error in RESTful request {e.args[-1]}')
                self.err_cnt += 1
                self.RESTful_success = False
            else:
                EtQ_folder_after = os.listdir(self.EtQ_folder)
                if (self.res.status == 200 and "Operation done successfully" in self.data.decode('utf-8')) \
                        and len(EtQ_folder_after) == 0:
                    self.error.append("Operation done successfully")
                    self.error.append(f'EtQ Server Response: {self.res.reason} Status: {self.res.status}')
                    logging.info("Operation done successfully") #TODO
                    logging.info(f'EtQ Server Response: {self.res.reason} Status: {self.res.status}')#TODO
                    self.RESTful_success = True
                    return

                else:
                    sleep(1)
                    self.err_cnt += 1
                    logging.debug(f'RestFul Error Count = {self.err_cnt}')
                    if self.err_cnt >= 20:
                        self.error.append(f'Status: {self.res.status} Attempts {self.err_cnt}')
                    print(self.error)
                    self.RESTful_success = False
        else:
            self.err_cnt = 0
            sleep(10)
