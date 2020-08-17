""" Large Bottles CIP Gateway Electronic Receipt
        Written by Shane Platt MTS Ventana
        Code Review by Dan Mayfield I.T Lead Consultant
        Version 1.00
        05AUG2020
"""
import json
import logging
from time import sleep
import AllenBradley
import FileTransfer as ft
import _Thread
import _XML
import mailer
from config import CIPConfig


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


def main():
    json_last_st = None
    json_date = None
    last_json_loaded = False
    load_values_cnt = 0
    error_data = []
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')  # filename='Example.log',
    logging.info('Start of Program')
    logging.info('Loading CIP_gateway.ini')
    config_ini = CIPConfig()
    local_folder = config_ini.config['FOLDER_LOCATIONS']['local_folder']
    ab = AllenBradley.Data(config_ini, error_data)
    abStrip = AllenBradley.Strip(error_data)
    mail = mailer.Email(config_ini)
    thread2 = _Thread.Monitor(config_ini, ab, error_data, mail)
    thread2.start()
    xml = _XML.CreateXml(ab, config_ini, thread2, error_data)
    write_files = ft.TransferFiles(config_ini, xml, thread2, error_data)

    logging.info('Attempting to Load PLC Data')

    while True:  # Main Loop
        # last_json_loaded is used to determine if the last saved Stop Time has been loaded from the Json File
        if not last_json_loaded:
            try:
                f = open(f'{local_folder}/mydata.json')
                json_load = json.load(f)
            except Exception as e:
                error_data.append(f'Json Load failed {e.args[-1]}')
                error_data.append("Setting default last start time to 00:00:00")
                json_date = "1/1/1970"
                json_last_st = "00:00:00"
                last_json_loaded = True
            else:
                json_last_st = (json_load['Cycle_Stop_Time'])  # Loading last CIP Stop Time from a Json file
                json_date = (json_load['Cycle_Date'])  # Loading last CIP Date from a Json file
                last_json_loaded = True

        try:
            # if an error is present in the list error_data than run emailer
            if error_data:
                er = mail.SendEmail(error_data)  # er = Email Response
                if er:
                    logging.info(er)
        except Exception as e:
            error_data.append(f'{e.args[-1]} Retrying')

        else:
            # Confirm that both CIP_cycleStopTime, thread2.CIP_LastCycle_Date
            # and json_date and Json_last_st have been written and are all Strings
            args = (thread2.CIP_cycleStopTime, thread2.CIP_LastCycle_Date, json_last_st, json_date)
            if is_string(*args):
                ee = eval_date_time(*args)
                if (ee and thread2.init_new_receipt) or \
                        (ee and thread2.first_time_running):
                    xml.CurrentReceiptSaved = False
                    thread2.first_time_running = False
                    thread2.init_new_receipt = False
                    logging.info(f'Last Receipt Stop Time:{json_last_st}')
                    logging.info(f'New Receipt Stop Time:{thread2.CIP_cycleStopTime}')
                    logging.info(f'Last Receipt Date:{json_date}')
                    logging.info(f'New Receipt Date:{thread2.CIP_LastCycle_Date}')
                    ret_ab_load = False  # *****************
                    stripped_header = ""  # * Clears Last   *
                    stripped_alarm = ""  # * Receipt Values*

                    while load_values_cnt <= 20:
                        load_values_cnt = + 1
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
                            """  This allows the GUI to Display the log file """

                            for line in split_header:
                                if line:
                                    logging.info(line)

                            logging.info(ab.raw_wash_data)

                        try:
                            xml.SaveFile()
                            if xml.StopCycle.text != json_last_st:
                                json_last_st = thread2.CIP_cycleStopTime
                                json_date = thread2.CIP_LastCycle_Date
                                write_files.OutboundFolder(xml.fileName)
                                # After latest receipt
                                json_dict = {'Cycle_Date': ab.raw_header.Value[2],
                                             'Cycle_Stop_Time': ab.raw_header.Value[17]}
                                with open(f'{local_folder}\\mydata.json', 'w') as f:
                                    json.dump(json_dict, f)
                                last_json_loaded = False
                                write_files.file_in_EtQ = False
                                write_files.EtQfolder()
                            else:
                                thread2.new_receipt_trigger = False
                            if write_files.file_in_EtQ:
                                write_files.RESTfulCall()

                        except Exception as e:
                            error_data.append(e.args[-1])

                        else:
                            if write_files.RESTful_success:
                                logging.info(f'EtQ Response: {write_files.res.reason}')
                                logging.info('EtQ process completed')
                                write_files.RESTful_success = False
                            else:
                                error_data.append('No response from EtQ')

                elif not thread2.init_new_receipt and load_values_cnt:  # Resets After Receipt was saved
                    sleep(5)
                    xml.CurrentReceiptSaved = False
                    load_values_cnt = 0
                    write_files.receipt_count = 0
                else:
                    thread2.first_time_running = False
                    thread2.init_new_receipt = False


if __name__ == "__main__":
    main()
