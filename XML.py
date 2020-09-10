import os
import xml.etree.ElementTree as xml
from datetime import datetime

from CIP_Utilities import CreateFolder


class CreateXml:
    def __init__(self, plc, Config, Thread, EL, Error):
        self.CurrentReceiptSaved = False
        self.el = EL
        self.error = Error
        self.id_time = None
        self.error_counter = 0
        self.config = Config
        self.EtQ_folder = Config.EtQ_folder
        self.working_folder = Config.local_folder
        self.archive_folder = Config.archive_folder
        self.outbound_folder = Config.outbound_folder
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
            self.el.logger.warning(e.args[-1])
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
            CreateFolder(self.archive_folder)
        if not self.CurrentReceiptSaved:
            try:
                self.el.logger.info(f'Changing to Archive Folder {self.archive_folder}')
                os.chdir(self.archive_folder)
            except Exception as e:
                self.error.append(f'Exception Catch {e.args[1]}')
                raise Exception(self.error)
            else:
                self.el.logger.info(f'Saving {self.fileName} in {self.archive_folder}')
                with open(self.fileName, "wb") as files:
                    self.tree.write(files)
                    if os.path.exists(self.fileName):
                        self.el.logger.info(f'({self.fileName}) was successfully saved in folder: {os.getcwd()}')
                    else:
                        self.error.append('Write Failed')
                        self.error.append(f'Unable to Write {self.fileName} to {self.outbound_folder} '
                                          f'Max Attempts Reached: {self.error_counter}')
                        raise Exception(self.error)
                    self.CurrentReceiptSaved = True
