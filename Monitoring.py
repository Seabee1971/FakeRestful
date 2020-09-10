"""This creates the class for the second thread
    and then will Monitor the folder locations and PLC connection"""

from threading import Thread

from pylogix import PLC


class PLCTags(Thread):
    def __init__(self, Config, AB, Error, EL, Mail):
        self.el = EL
        self.first_time_running = True
        self.email_sent = False
        self.print_wash_control = None
        self.Config = Config
        self.ab = AB
        self.error = Error
        self.mail = Mail
        self.outbound_folder = Config.outbound_folder
        with PLC() as self.clx:
            self.clx.IPAddress = Config.IPAddress
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
        w = 0
        """Monitors PLC Tag:
            New receipt trigger is ¨Program:PRINT.Print_Wash_Control.Print_Control.6
             to determine when to create new receipt  """
        while (w := w + 1) < 10 and not self.init_new_receipt:
            try:
                self.print_wash_control = self.clx.Read("Program:PRINT.Print_Wash_Control.Print_Control.6")
                receipt_date = self.clx.Read("Program:PRINT.Print_Form_Header[2]")
                stop_time = self.clx.Read("Program:PRINT.Print_Form_Header[17]")
                assert self.print_wash_control.Status == "Success", 'failed to read print_wash_control.Status'
                assert receipt_date.Status == "Success", 'failed to read receipt_date.Status'
                assert stop_time.Status == "Success", 'failed to read stop_time status'

            except Exception as e:
                self.num_connect_attempts += 1
                self.plc_status_failed_count += 1
                if self.plc_status_failed_count >= 10:
                    self.error.append(f'PLC connection failed {e.args[-1]}')
                    self.plc_status_failed_count = 0
                return False

            else:
                if not self.new_receipt_trigger:
                    self.new_receipt_trigger = True if self.print_wash_control.Value else False
                elif not self.init_new_receipt or self.first_time_running:
                    self.init_new_receipt = True
                    self.CIP_LastCycle_Date = receipt_date.Value
                    self.CIP_cycleStopTime = stop_time.Value
                    return True

    def plc_hand_shake(self):
        """  Monitors PLC Connection:
                  Confirms Good Connection     """

        try:
            self.confirm_connection = self.print_wash_control.Status
            if self.confirm_connection and self.num_connect_attempts:
                return

        except Exception as e:
            self.num_connect_attempts = self.num_connect_attempts + 1

            self.el.logger.warning(f'PLC connection {e.args[0]} Attempt {self.num_connect_attempts} of 50')
            if self.num_connect_attempts >= 5:  # After 50 tries HandShake Fails.
                self.error.append(f'Unable to Connect to {self.clx.IPAddress} after 50 Attempts')
                self.num_connect_attempts = 0

        else:
            if self.num_connect_attempts == 0:
                self.el.logger.info(f'PLC IP Address is: {self.clx.IPAddress}')
                self.el.logger.info(f'PLC Connection Established = {self.confirm_connection}')
            self.num_connect_attempts = self.num_connect_attempts + 1  # Error count
            self.el.logger.info('Waiting on Next Receipt')
            self.error.clear()
