import json
import logging.handlers
import os
from configparser import ConfigParser


class CIPConfig:
    """ This function loads the file "CIP_Gateway.ini"  """

    def __init__(self, err):
        w = 0
        self.loadFeedback = None
        config = ConfigParser()
        while not self.loadFeedback and (w := w + 1) < 10:
            try:
                config.read('CIP_gateway.ini')
                self.log_folder = config['FOLDER_LOCATIONS']['log_folder']
                self.log_filename = config['LOGGING']['log_filename']
                self.local_folder = config['FOLDER_LOCATIONS']['local_folder']
                self.EtQ_folder = config['FOLDER_LOCATIONS']['etq_folder']
                self.archive_folder = config['FOLDER_LOCATIONS']['archive_folder']
                self.outbound_folder = config['FOLDER_LOCATIONS']['outbound_folder']
                self.etq_archive = config['FOLDER_LOCATIONS']['etq_archive']
                self.IPAddress = config['DEFAULT']['ip_address']

                self.email_active = bool(config["EMAIL_SETTINGS"].getboolean('email_active'))
                self.delay_time = int(config["EMAIL_SETTINGS"]["time_delay"])
                self.mail_host = config["EMAIL_SETTINGS"]["mail_host"]
                self.mail_port = config["EMAIL_SETTINGS"]["mail_port"]
                self.Subject = config["EMAIL_SETTINGS"]["subject_line"]
                self.From = config["EMAIL_SETTINGS"]["from"]
                self.To = config["EMAIL_SETTINGS"]["to"]
                #  RESTful Settings
                self.http_client = config['RESTFUL_PARAMS']['http_client']
                self.get_request = config['RESTFUL_PARAMS']['get_request']
                self.payload = config['RESTFUL_PARAMS']['payload']
                self.header_auth = config['RESTFUL_PARAMS']['header_auth']
                self.header_basic = config['RESTFUL_PARAMS']['header_basic']
            except Exception as e:
                if w >= 9:
                    err.append(error_msg(e.args[-1]))
                    break
                self.load_failed()
            else:
                self.load_success()

    def load_success(self):
        self.loadFeedback = True
        return self.loadFeedback

    def load_failed(self):
        self.loadFeedback = False
        return self.loadFeedback


class CreateFolder:
    def __init__(self, folderName):
        self.folderName = folderName
        print(f'{self.folderName} does not exist. Creating Now')
        os.mkdir(self.folderName)
        if os.path.exists(self.folderName):
            print(f'{self.folderName} Created')
            os.chdir(self.folderName)
            print(f'Current Folder: {os.getcwd()}')


class Logger:
    def __init__(self, config):
        try:
            Config = config
            self.log_file_name = f'{Config.log_folder}/{Config.log_filename}'
            self.logger = logging.getLogger()
            self.handler = logging.handlers.TimedRotatingFileHandler(self.log_file_name, when="midnight",
                                                                     backupCount=10)
            self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                               datefmt='%m/%d/%Y %I:%M:%S %p')
            logging_level = logging.DEBUG
            self.handler.setFormatter(self.formatter)
            self.logger.addHandler(self.handler)
            self.logger.setLevel(logging_level)
            self.logger.info('Start of Program')
            self.logger.info('Loading CIP_gateway.ini')
            self.logger.info('Attempting to Load PLC Data')
        except Exception as ex:
            # handle unexpected script errors
            logging.exception("Unhandled error\n{}".format(ex))
            raise
        else:
            return


class Json:
    def __init__(self, Config, err):
        self.dict = dict
        self.err = err
        self.Config = Config
        self.StopTime = None
        self.ReceiptDate = None
        self.loaded = False
        self.Data = None

    def save(self):
        """Save Json Data After latest receipt"""
        self.dict = {'Cycle_Date': self.ReceiptDate,
                     'Cycle_Stop_Time': self.StopTime}
        with open(f'{self.Config.local_folder}\\mydata.json', 'w') as f:
            json.dump(self.dict, f)
        self.loaded = False
        return True

    def load(self):
        """Loads Json Data """
        w = 0
        while (w := w + 1) < 10:
            try:
                f = open(f'{self.Config.local_folder}/mydata.json')
                self.Data = json.load(f)

            except Exception as e:
                if w >= 9:
                    self.err.append(f'Json Load failed {e.args[-1]}')
                    self.err.append("Set default last Stop time to 00:00:00")
                    self.StopTime = "00:00:00"
                    self.ReceiptDate = "1/1/1970"
            else:
                self.StopTime = self.Data['Cycle_Stop_Time']
                self.ReceiptDate = self.Data['Cycle_Date']
                if is_string(self.StopTime, self.ReceiptDate):  # Confirms Json data was loaded as String
                    return True


def error_msg(*args):
    """ Iterates through the errors
    creates a list and calls emailer method."""
    return [err for err in args]


def eval_date_time(*args):
    """If length of temp is over 2 it means 2 different dates added and json data is different than plc data,
        create new receipt"""
    temp = []
    for val in args:
        if val not in temp:
            temp.append(val)
    return len(temp) > 2


def is_string(*args):
    """Confirms Both Date and Times read from the PLC
       and Json File have been loaded and are all Strings"""
    return all(type(val) == str for val in args)


def set_tags_off(thread, xml):
    if thread.new_receipt_trigger or thread.first_time_running:
        thread.running = False
        xml.CurrentReceiptSaved = False
        thread.first_time_running = False
        thread.init_new_receipt = False

