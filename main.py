import pathlib

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import PySimpleGUI as sg
import pydicom

def open_series(foldername):
    folderpath = pathlib.Path(foldername)
    if not folderpath.exists():
        sg.popup_error('Folder not found', no_titlebar=True)
        return None

    allfiles = [(x, pydicom.dcmread(x)) for x in folderpath.glob('*.dcm')]

    if not allfiles:
        sg.popup_error('No dicoms in folder', no_titlebar=True)
        return None, None

    allfiles.sort(key=lambda x: int(x[1]['InstanceNumber'].value))
    return allfiles

def mosaify(data):
    if len(data.shape) < 3:
        return data
    nacross = int(np.floor(np.sqrt(data.shape[0])))
    ndown = int(np.ceil(data.shape[0] / nacross))
    mdata = data.copy()
    mdata.resize(int(nacross*ndown), data.shape[1], data.shape[2])
    mdata = mdata.reshape((-1, mdata.shape[2]), order='F')\
        .reshape(mdata.shape[1], ndown, -1).reshape((int(mdata.shape[1]*ndown), -1), order='F')
    return mdata

def draw_figure(canvas, figure):
   tkcanvas = FigureCanvasTkAgg(figure, canvas)
   tkcanvas.draw()
   tkcanvas.get_tk_widget().pack(side='top', fill='both', expand=1)
   return tkcanvas

if __name__ == '__main__':
    dicom_path = pathlib.Path('/projects/lcni/dcm/lcni/Smith/xa30_test')
    sg.theme('Dark Blue 3')

    layout = [[sg.Text('Dicom folder')],
              [sg.Input(key='dicom', size=(120, None), enable_events=True),
               sg.FolderBrowse(key='browser', initial_folder=dicom_path)],
              [sg.Text('Frame'), sg.Spin([0], key='frame', enable_events=True), sg.Button('Exit')],
              [sg.Canvas(key='canvas', expand_x=True, expand_y=True)]
              ]

    window = sg.Window('Multiframe DICOM viewer', layout, resizable=True, finalize=True)

    fig,ax = plt.subplots()
    ax.set_axis_off()
    draw_figure(window['canvas'].TKCanvas, fig)
    dicom_data = None

    while True:
        event, values = window.read()
        #print(event, values)
        if event in (None, 'Exit'):  # if user closes window or clicks Exit
            break
        if event == 'dicom':
            dicom_data = open_series(values['dicom'])
            ax.clear()
            ax.set_axis_off()
            if dicom_data:
                window.Element('frame').Update(values=[x for x in range(0, len(dicom_data))], value=0)
                ax.set_title(dicom_data[0][0].name)
                ax.imshow(mosaify(dicom_data[0][1].pixel_array), cmap='gray')
            else:
                window.Element('frame').Update(values=[0], value=0)
            fig.canvas.draw()

        if event=='frame' and dicom_data:
            frameNo = values['frame']
            ax.clear()
            ax.set_title(dicom_data[frameNo][0].name)
            ax.set_axis_off()
            ax.imshow(mosaify(dicom_data[frameNo][1].pixel_array), cmap='gray')
            fig.canvas.draw()

    window.close()


