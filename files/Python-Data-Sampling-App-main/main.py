import csv
import xlsxwriter
import queue
import re
import threading
from time import perf_counter
#import datetime
import os
import sys
from datetime import datetime

import PySimpleGUI as sg

import serial_comm as my_serial


class Application:

    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        baud_rate = 250000
        gui_queue = queue.Queue()
        serial_connector = my_serial.SerialObj(baud_rate)

        headerFont = ('Helvetica', 16)
        middleFont = ('Helvetica', 14)
        contextFont = ('Helvetica', 12)
        smallFont = ('Helvetica', 10)
        sg.theme('DarkBlue')

        layout = [[sg.Text('DATA LOGGER VIA SERIAL', font=headerFont)],
                  [sg.Text('Select your serial port', font=contextFont),
                   sg.Button('Serial Port Reload', size=(20, 1), font=smallFont)],
                  [sg.Listbox(values=[x[0] for x in my_serial.SerialObj.get_ports()],
                              size=(40, 6),
                              key='_SERIAL_PORT_LIST_',
                              font=contextFont,
                              enable_events=True)],
                  [sg.Text('', key='_SERIAL_PORT_CONFIRM_', size=(40, 1), font=middleFont, ), ],
                  [sg.Text('Baud Rate: {} bps'.format(baud_rate), size=(40, 1), font=middleFont, ), ],
                  [sg.Text('How many samples?', font=contextFont, ), sg.VerticalSeparator(),
                   sg.Input(do_not_clear=True, enable_events=True, key='_SAMPLE_IN_', font=contextFont, )],

                  [sg.HorizontalSeparator()],
                  [sg.Text('Serial Comm Status', font=contextFont, pad=((6, 0), (20, 0))), ],
                  [sg.Text('', key='_OUTPUT_', size=(40, 2), font=middleFont, ), ],
                  [sg.Button('Start', key='_ACT_BUTTON_', font=middleFont, size=(40, 1), pad=((0, 0), (0, 0)))],
                  [sg.Button('Exit', font=middleFont, size=(40, 1), pad=((0, 0), (20, 0)))],
                  [sg.Text('ThatProject - Version: 0.1', justification='right', size=(50, 1), font=smallFont, ), ]]

        self.window = sg.Window('Simple Serial Application', layout, size=(420, 540), keep_on_top=True)

        while True:
            event, values = self.window.Read(timeout=100)

            if event is None or event == 'Exit':
                break

            if event == 'Serial Port Reload':
                self.get_ports()

            if event == '_SERIAL_PORT_LIST_':
                self.window['_SERIAL_PORT_CONFIRM_'].update(value=self.window['_SERIAL_PORT_LIST_'].get()[0])

            if event == '_SAMPLE_IN_' and values['_SAMPLE_IN_'] and values['_SAMPLE_IN_'][-1] not in ('0123456789'):
                self.window['_SAMPLE_IN_'].update(values['_SAMPLE_IN_'][:-1])

            if event == '_ACT_BUTTON_':
                print(self.window[event].get_text())
                if self.window[event].get_text() == 'Start':

                    if len(self.window['_SERIAL_PORT_LIST_'].get()) == 0:
                        self.popup_dialog('Serial Port is not selected yet!', 'Serial Port', contextFont)

                    elif len(self.window['_SAMPLE_IN_'].get()) == 0:
                        self.popup_dialog('Set Sampling Count', 'Sampling Number Error', contextFont)

                    else:
                        self.stop_thread_trigger = False
                        self.thread_serial = threading.Thread(target=self.start_serial_comm,
                                                              args=(serial_connector,
                                                                    self.window[
                                                                        '_SERIAL_PORT_LIST_'].get()[
                                                                        0],
                                                                    int(self.window[
                                                                            '_SAMPLE_IN_'].get()),
                                                                    gui_queue, lambda: self.stop_thread_trigger),
                                                              daemon=True)
                        self.thread_serial.start()
                        self.window['_ACT_BUTTON_'].update('Stop')

                else:
                    self.stop_thread_trigger = True
                    self.thread_serial.join()
                    self.window['_ACT_BUTTON_'].update('Start')

            try:
                message = gui_queue.get_nowait()
            except queue.Empty:
                message = None
            if message is not None:
                self.window['_OUTPUT_'].Update(message)
                if 'Done' in message:
                    self.window['_ACT_BUTTON_'].update('Start')
                    #self.popup_dialog(message, 'Success', contextFont)

        self.window.Close()

    def popup_dialog(self, contents, title, font):
        sg.Popup(contents, title=title, keep_on_top=True, font=font)

    def get_ports(self):
        self.window['_SERIAL_PORT_LIST_'].Update(values=[x[0] for x in my_serial.SerialObj.get_ports()])

    def start_serial_comm(self, serial_connector, serialport, sample_num, gui_queue, stop_thread_trigger):
        now = datetime.now()
        # Create a workbook and add a worksheet.
        self.workbook = xlsxwriter.Workbook("test_" + now.strftime("%d_%m_%Y-%H_%M_%S") + ".xlsx")
        # Add a worksheet to hold the data.
        self. worksheet = self.workbook.add_worksheet()
        # Add a chartsheet. A worksheet that only holds a chart.
        self.chartsheet = self.workbook.add_chartsheet()
        # Add a format for the headings.
        bold = self.workbook.add_format({'bold': 1})
        dualplaceformat = self.workbook.add_format({'num_format': '#,##0.00'})

        # Add the worksheet data that the charts will refer to.
        headings = ['Time', 'Pressure']
        self.worksheet.write_row('A1', headings, bold)

        start_time = 0

        serial_connector.connect(serialport)
        if serial_connector.is_connect():

            gui_queue.put('Serial Connected!!')

            n = 0
            #file='LogData_{}.csv'.format(str(datetime.datetime.timestamp(datetime.datetime.now())))
            while n < sample_num:
                try:
                    if stop_thread_trigger():
                        break

                    data = serial_connector.get_data()
                    if data is not None:
                        if n == 0:
                            gui_queue.put(' - Data Transmitting ::: Wait! ')
                            start_time = perf_counter()
                    #if len(decode_string.split(',')) == 6:
                        else:
                            #decode_string = data.decode('utf-8')
                            #print(decode_string)
                            percent = n / sample_num * 100
                            #self.csv_writer(file, n, decode_string)
                            self.worksheet.write(n, 0, round((perf_counter() - start_time),2))
                            self.worksheet.write(n, 1, float(data.strip()))

                            if percent % 5 == 0:
                                gui_queue.put('Saving to CSV File: {}% complete'.format(int(percent)))

                        n += 1

                except OSError as error:
                    print(error)

                except UnicodeDecodeError as error:
                    print(error)

        serial_connector.disconnect()
        time_taken = (perf_counter() - start_time)
        sampling_rate = sample_num / time_taken
        gui_queue.put('Sampling Rate: {} hz ::: Done!'.format(int(sampling_rate)))
        
        # Create a new bar chart.
        chart1 = self.workbook.add_chart({'type': 'line'})  # , 'subtype': 'smooth'})  # scatter
        endofchart = n-1
        # # Configure the first series.
        # chart1.add_series({
        #     'Time':             '=Sheet1!$A$2:$A$' + str(endofchart),
        #     'Bar Width':        '=Sheet1!$B$2:$B$' + str(endofchart),
        #     'Bar Position':     '=Sheet1!$C$2:$C$' + str(endofchart),
        #     'Head Position':    '=Sheet1!$D$2:$D$' + str(endofchart),
        # })

        # # Configure a second series. Note use of alternative syntax to define ranges.
        # # [sheetname, first_row, first_col, last_row, last_col]
        chart1.add_series({
            'name':   '',  # 'Time',
            'values': ['Sheet1', 1, 0, endofchart, 0],
            'categories': ['Sheet1', 1, 0, endofchart, 0],
            'line':   {'none': True},
            # 'line':       {'color': 'orange'},
        })
        chart1.add_series({
            'name':     'Pressure',
            'values': ['Sheet1', 1, 1, endofchart, 1],
            'categories': ['Sheet1', 1, 1, endofchart, 1],
            'line': {'color': 'blue'},
            'line':   {'width': 1.5},
            'smooth':     True,
        })

        # Set an Excel chart style.
        chart1.set_style(4)
        # Add a chart title and some axis labels.
        chart1.set_title({'name': 'Results of sample analysis'})
        chart1.set_x_axis({'name': 'Time', 'major_gridlines': {'visible': False}})
        chart1.set_y_axis({'name': 'Pressure (hPa)', 'major_gridlines': {'visible': False}})

        
        # Add the chart to the chartsheet.
        self.chartsheet.set_chart(chart1)

        # Display the chartsheet as the active sheet when the workbook is opened.
        self.chartsheet.activate()

        self.workbook.close()
        return

    def csv_writer(self, filename, index, data):
        with open(filename, 'a') as f:
            writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_NONE, dialect=csv.excel, lineterminator='\n', escapechar=' ')
            writer.writerow([re.sub(r"\s", "", data)])  # Dummy data for magnetometers, it doesn't use magnetometer in matlab.


if __name__ == '__main__':
    Application()
