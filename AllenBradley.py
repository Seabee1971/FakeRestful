import logging

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
