import os
from cipUtilities import CIPConfig
import shutil
from time import sleep


print(os.getcwd())
os.chdir('c:\\scripts\\CIP_Gateway')
print(os.getcwd())
cip_config = CIPConfig()
EtQ_folder = cip_config.config['FOLDER_LOCATIONS']['etq_folder']
EtQ_archive_folder = cip_config.config['FOLDER_LOCATIONS']['etq_archive']
archive_folder = cip_config.config['FOLDER_LOCATIONS']['archive_folder']
outbound_folder = cip_config.config['FOLDER_LOCATIONS']['outbound_folder']
log_folder = cip_config.config['FOLDER_LOCATIONS']['log_folder']
local_folder = cip_config.config['FOLDER_LOCATIONS']['local_folder']
while True:
    if os.listdir(EtQ_folder):
        sleep(1)
        for x, file in enumerate(os.listdir(EtQ_folder), 1):
            shutil.move(f'{EtQ_folder}/{file}', EtQ_archive_folder)
        print(f'Moved {x} files')
