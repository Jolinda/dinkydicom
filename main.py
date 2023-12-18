# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import pathlib

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import PySimpleGUI as sg
import pydicom

def ShowSeries(foldername):
    folderpath = pathlib.Path(foldername)
    if not folderpath.exists():
        sg.popup_error('Folder not found', no_titlebar=True)
        return None

    ## testing
    firstfile = next(folderpath.glob('*.dcm'), None)
    if not firstfile:
        sg.popup_error('No dicoms in folder', no_titlebar=True)
        return None

    return ShowDicom(firstfile)

def ShowDicom(filename):
    if not filename.exists():
        sg.popup_error('File not found', no_titlebar=True)
        return None

    img = pydicom.dcmread(filename)
    print(filename)
    print(img.pixel_array.shape)
    if len(img.pixel_array.shape) > 2:
        data = mosaify(img.pixel_array)
    else:
        data = img.pixel_array

    fig, ax = plt.subplots()
    ax.set_title(filename.name)
    ax.imshow(data, cmap='gray')
    ax.set_axis_off()
    return fig


def mosaify(data):
    nacross = int(np.floor(np.sqrt(data.shape[0])))
    ndown = int(np.ceil(data.shape[0] / nacross))
    mdata = data.copy()
    mdata.resize(int(nacross*ndown), data.shape[1], data.shape[2])
    mdata = mdata.reshape((-1, mdata.shape[2]), order='F')\
        .reshape(mdata.shape[1], ndown, -1).reshape((int(mdata.shape[1]*ndown), -1), order='F')
    return mdata

# from https://www.tutorialspoint.com/pysimplegui/pysimplegui_matplotlib_integration.htm
def draw_figure(canvas, figure):
   tkcanvas = FigureCanvasTkAgg(figure, canvas)
   tkcanvas.draw()
   tkcanvas.get_tk_widget().pack(side='top', fill='both', expand=1)
   return tkcanvas

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    dicom_path = pathlib.Path('/projects/lcni/dcm/lcni/Smith/xa30_test')
    sg.theme('Dark Blue 3')

    layout = [[sg.Button('Plot'), sg.Button('Mosaic'), sg.Button('Exit')],
              [sg.Text('Dicom folder')],
              [sg.Input(key='dicom', size=(120, None)),
               sg.FolderBrowse(key='dicom_browser', initial_folder=dicom_path)],
              [sg.Canvas(key='canvas')]
              ]

    # Create the Window
    window = sg.Window('Multiframe DICOM viewer', layout)
    # Event Loop to process "events" and get the "values" of the inputs
    figure_canvas = None
    while True:
        event, values = window.read()
        print(event, values)
        if event in (None, 'Exit'):  # if user closes window or clicks Exit
            break
        if event == 'Plot':
            dicom_figure = ShowSeries(values['dicom'])
            if figure_canvas:
                figure_canvas.get_tk_widget().forget()
                plt.close('all')
            figure_canvas = draw_figure(window['canvas'].TKCanvas, dicom_figure)

    window.close()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
