"""This creates the class for the second thread
    and then will Monitor the folder locations and PLC connection"""
import logging
from threading import Thread


from pylogix import PLC


class Monitor(Thread):
    def __init__(self, Config, AB, Error, Mail):
        self.first_time_running = True
        self.email_sent = False
        self.print_wash_control = None
        self.Config = Config
        self.ab = AB
        self.error = Error
        self.mail = Mail
        self.outbound_folder = Config.config['FOLDER_LOCATIONS']['outbound_folder']
        with PLC() as self.clx:
            self.clx.IPAddress = self.Config.config['DEFAULT']['ip_address']
        self.confirm_connection = None
        self.new_receipt_trigger = None
        self.init_new_receipt = False
        self.num_connect_attempts = 0
        self.CIP_LastCycle_Date = None
        self.CIP_cycleStopTime = None
        self.plc_status_failed_count = 0

        Thread.__init__(self)
        self.running = True

    def run(self):
        """ Main Loop for Thread  """
        while self.running:
            if self.check_print_status():
                self.plc_hand_shake()

    def check_print_status(self):
        """Monitors PLC Tag:
            New receipt trigger is ¨Program:PRINT.Print_Wash_Control.Print_Control.6
             to determine when to create new receipt  """
        try:
            self.print_wash_control = self.clx.Read("Program:PRINT.Print_Wash_Control.Print_Control.6")
            if self.print_wash_control.Status != "Success":
                raise Exception(' to load new receipt flag')
            self.new_receipt_trigger = True if self.print_wash_control.Value else False
            self.confirm_connection = self.clx.GetPLCTime().Status
            receipt_date = self.clx.Read("Program:PRINT.Print_Form_Header[2]")
            stop_time = self.clx.Read("Program:PRINT.Print_Form_Header[17]")

        except Exception as e:
            self.num_connect_attempts += 1
            self.plc_status_failed_count += 1
            if self.plc_status_failed_count >= 10:
                self.error.append(f'PLC connection failed {e.args[-1]}')
                self.plc_status_failed_count = 0
            return False

        else:
            if (self.new_receipt_trigger and not self.init_new_receipt) or self.first_time_running:
                self.init_new_receipt = self.new_receipt_trigger
                if receipt_date.Status == "Success" and stop_time.Status == "Success":
                    self.CIP_LastCycle_Date = receipt_date.Value
                    self.CIP_cycleStopTime = stop_time.Value
                    return True
                else:
                    self.plc_status_failed_count += 1
                    if self.plc_status_failed_count >= 5:
                        lst = receipt_date.Status, stop_time.Status
                        for status in lst:
                            if status != "Success":
                                self.error.append(status)
                        self.plc_status_failed_count = 0  # Reset Count
                    return False
            return True

    def plc_hand_shake(self):
        """  Monitors PLC Connection:
                  Confirms Good Connection     """

        try:
            if self.confirm_connection and self.num_connect_attempts:
                return

        except Exception as e:
            self.num_connect_attempts = self.num_connect_attempts + 1
            logging.warning(f'PLC connection {e.args[0]} Attempt {self.num_connect_attempts} of 50')
            if self.num_connect_attempts >= 5:  # After 50 tries HandShake Fails.
                self.error.append(f'Unable to Connect to {self.clx.IPAddress} after 50 Attempts')
                self.num_connect_attempts = 0

        else:
            if self.num_connect_attempts == 0:
                logging.info(f'PLC IP Address is: {self.clx.IPAddress}')
                logging.info(f'PLC Connection Established = {self.confirm_connection}')
            self.num_connect_attempts = self.num_connect_attempts + 1  # Error count
            logging.info('Waiting on Next Receipt')
            self.error.clear()
