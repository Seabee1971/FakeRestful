"""
        Reads Init File
        """

import logging
import os
from configparser import ConfigParser


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
