import json
import tkinter.font as tkFont
import xml.etree.ElementTree as ET
from tkinter import *
from tkinter import filedialog
from config import CIPConfig
import tkinter.scrolledtext

# Loads Config Init files
cip_config = CIPConfig()
EtQ_folder = cip_config.config['FOLDER_LOCATIONS']['etq_folder']
archive_folder = cip_config.config['FOLDER_LOCATIONS']['archive_folder']
outbound_folder = cip_config.config['FOLDER_LOCATIONS']['outbound_folder']
log_folder = cip_config.config['FOLDER_LOCATIONS']['log_folder']
local_folder = cip_config.config['FOLDER_LOCATIONS']['local_folder']


def browseReceipts():
    filename = filedialog.askopenfilename(initialdir=archive_folder, title="Select a File",
                                          filetypes=(("XML files",
                                                      "*.xml*"),
                                                     ("XML files",
                                                      "*.*xml*")))

    text_box.delete(1.0, END)
    if filename:
        label_file_explorer.configure(text="File Opened: " + filename)
        openXMLFile(filename)


def browseLogs():
    filename = filedialog.askopenfilename(initialdir=log_folder, title="Select a File",
                                          filetypes=(("Log files",
                                                      "*.log*"),
                                                     ("Log files",
                                                      "*.*log*")))

    text_box.delete(1.0, END)
    if filename:
        label_file_explorer.configure(text="File Opened: " + filename)
        openTXTFile(filename)


def openTXTFile(filename):
    f = open(filename, "r")
    lines = f.readlines()
    for line in lines:
        text_box.insert(END, line)


def openXMLFile(file_name):
    a = {}
    tree = ET.parse(file_name)
    root = tree.getroot()
    for child in root:
        a.update({child.tag: child.text})
        b = child.tag
        c = child.text
        try:
            d = b + " = " + c + "\r\n"
        except Exception as e:
            if e:
                pass
        else:
            text_box.insert(END, d)


def json_data():
    jv = ""
    f = open(f'{local_folder}/mydata.json')
    jsonData = json.load(f)

    for keys, values in jsonData.items():
        jv = jv + keys + " = " + values + "\r\n"

    return text_box.insert(END, jv)


# Create the root window
window = Tk()
# Set window title
window.title('CIP Gateway Receipt Viewer')

# Set window size
window.geometry("800x600")
window.attributes("-fullscreen", True)

# Font Configuration
fontStyle = tkFont.Font(family="Comic Sans", size=12)

# Set window background color
window.config(background="white")
image = PhotoImage(file="VentanaLogo1.png")
image1 = PhotoImage(file="Roche-Logo1.png")
smaller_image = image.subsample(2, 2)
smaller_image1 = image1.subsample(3, 3)

# Create a File Explorer label
label_logo_explorer = Label(window, image=smaller_image)
label_Roche_explorer = Label(window, image=smaller_image1)

label_file_explorer = Label(window, font=fontStyle,
                            text="CIP Gateway Receipt Viewer",
                            width=125, height=4,
                            bg="white", fg="DarkBlue")

button_explore_text = Button(window, font=fontStyle,
                             text="Browse Receipts", height=2, width=15,
                             command=browseReceipts, bg="RoyalBlue2")

button_explore_xml = Button(window, font=fontStyle,
                            text="Browse Logs", height=2, width=15,
                            command=browseLogs, bg="RoyalBlue2")

button_json_values = Button(window, font=fontStyle,
                            text="Date/Time Stamp", height=2, width=15,
                            command=json_data, bg="RoyalBlue2")

button_exit = Button(window, font=fontStyle,
                     text="Exit", height=2, width=15,
                     command=exit, bg="RoyalBlue2")
S = Scrollbar(window)
text_box = tkinter.scrolledtext.ScrolledText(window, height=45, width=150)
text_box.config(yscrollcommand=S.set)

text_json = Text(window, height=40, width=20)
label_file_explorer.grid(column=1, row=1)
label_logo_explorer.grid(column=0, row=1)
label_Roche_explorer.grid(column=2, row=1)

button_explore_text.place(height=50, x=1, y=75)

button_explore_xml.place(height=50, x=1, y=150)

button_exit.place(height=50, x=1, y=225)

button_json_values.place(height=50, x=1, y=300)

text_box.grid(column=1, row=4)

# Let the window wait for any events
window.mainloop()

