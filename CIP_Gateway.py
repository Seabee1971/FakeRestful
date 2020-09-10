""" Large Bottles CIP Gateway Electronic Receipt Generator
        Written by Shane Platt MTS Ventana
        Code Review by Dan Mayfield I.T. Lead Consultant
        Version 1.00
        09SEP2020
"""


from time import sleep

import AllenBradley
import CIP_Utilities as Util
import FileTransfer as ft
import Monitoring
import XML
import mailer
from CIP_Utilities import CIPConfig
from CIP_Utilities import Json
from CIP_Utilities import Logger


def main():
    cnt = 0
    error_data = []
    Config = CIPConfig(error_data)
    log = Logger(Config)
    ab = AllenBradley.Data(Config, log, error_data)
    abStrip = AllenBradley.Strip(log, error_data)
    mail = mailer.Email(Config, log)
    thread2 = Monitoring.PLCTags(Config, ab, error_data, log, mail)
    thread2.start()
    xml = XML.CreateXml(ab, Config, thread2, log, error_data)
    write_files = ft.TransferFiles(Config, xml, thread2, log, error_data)
    json = Json(Config, error_data)

    while True:  # Main Loop
        try:
            if not json.loaded:
                json.loaded = json.load()

            if error_data:
                er = mail.SendEmail(error_data)  # er = Email Response
                if er:
                    log.logger.error(er)
        except Exception as e:
            error_data.append(f'{e.args[-1]} Retrying')

        else:
            args = (thread2.CIP_cycleStopTime, thread2.CIP_LastCycle_Date, json.StopTime, json.ReceiptDate)
            """ Confirm that CIP_cycleStopTime, thread2.CIP_LastCycle_Date
                and json_date and Json_last_st have been written and are all Strings """
            if Util.is_string(*args) and Util.eval_date_time(*args):
                Util.set_tags_off(thread2, xml)
                ret_ab_load = False
                while (cnt := cnt + 1) <= 20:
                    ret_ab_load = ab.LoadValues()  # Calls Method load_values from AllenBradley Data Class
                    if ret_ab_load:
                        break
                else:
                    error_data.append("Failed to Load PLC Data")

                if ret_ab_load and not xml.CurrentReceiptSaved:
                    stripped_header = abStrip.ReturnString(ab.raw_header.Value)
                    stripped_alarm = abStrip.ReturnString(ab.raw_alarms.Value)
                    xml.BuildFile(stripped_header, stripped_alarm, ab.raw_wash_data)

                    try:
                        split_header = stripped_header.split('\t')
                    except Exception as e:
                        error_data.append(f'Error {e.args[-1]}')
                    else:
                        for line in split_header:
                            if line:
                                log.logger.info(line)
                        newline = ab.raw_wash_data.split('\n')
                        raw_wash_data = ""
                        for line1 in newline:
                            if line1.startswith('--'):
                                raw_wash_data = raw_wash_data + '\n'
                            elif line1:
                                raw_wash_data = raw_wash_data + line1 + '\n'
                        # print(raw_wash_data)
                        log.logger.info(raw_wash_data)

                    try:
                        if xml.StopCycle.text != json.StopTime:
                            xml.SaveFile()
                            json.StopTime = xml.StopCycle.text
                            json.ReceiptDate = xml.Date.text
                            ret = json.save()
                            log.logger.info(f'Json Data Updated: {ret}')
                            thread2.running = True
                            write_files.OutboundFolder(xml.fileName)
                            write_files.file_in_EtQ = False
                            write_files.EtQfolder()

                        else:
                            thread2.new_receipt_trigger = False
                            thread2.running = True
                        if write_files.file_in_EtQ:
                            # TODO write_files.RESTfulCall()
                            write_files.RESTful_success = True

                    except Exception as e:
                        error_data.append(e.args[-1])

                    else:
                        if write_files.RESTful_success:
                            # TODO log.logger.info(f'EtQ Response: {write_files.res.reason}')
                            log.logger.info('EtQ process completed')
                            write_files.RESTful_success = False
                        else:

                            if write_files.res:
                                error_data.append(f'Error = {error_data}\r'
                                                  f'EtQ Response: {write_files.res.reason}')
                                log.logger.info(f'\rWaiting on Next Receipt')
                            else:
                                error_data.append(f'Error = {error_data}\r EtQ Response: None')
                                log.logger.info('Waiting on Next Receipt')
                        error_data.clear()

            elif not thread2.init_new_receipt and cnt:  # Resets After Receipt was saved
                sleep(5)
                xml.CurrentReceiptSaved = False
                cnt = 0
                write_files.receipt_count = 0
            else:
                thread2.running = True
                thread2.first_time_running = False
                thread2.init_new_receipt = False


if __name__ == "__main__":
    main()
