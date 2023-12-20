import pathlib

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import PySimpleGUI as sg
import pydicom

# todo: message while data loads. Does not work currently; may need threads
# todo: user change vmin, vmax

def open_series(foldername):
    folderpath = pathlib.Path(foldername)
    if not folderpath.exists():
#        sg.popup_error('Folder not found', no_titlebar=True)
        return None, None, None

    allfiles = [(x, pydicom.dcmread(x)) for x in folderpath.glob('*.dcm')]

    if not allfiles:
#        sg.popup_error('No dicoms in folder', no_titlebar=True)
        return None, None, None

    allfiles.sort(key=lambda x: int(x[1]['InstanceNumber'].value))
    vmin = min([x['SmallestImagePixelValue'].value for _,x in allfiles])
    vmax = max([x['LargestImagePixelValue'].value for _,x in allfiles])

    allfiles = [x for x,_ in allfiles]

    return allfiles, vmin, vmax

def get_data(filename):
    img = pydicom.dcmread(filename)
    return mosaify(img.pixel_array)

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
              [sg.Input(key='-FOLDER OPEN-', size=(120, None), enable_events=True),
               sg.FolderBrowse(initial_folder=dicom_path)],
              [sg.Text('Frame'), sg.Spin([0], key='-FRAME-', enable_events=True), sg.Button('Exit')],
              [sg.Canvas(key='-CANVAS-', expand_x=True, expand_y=True)],
              [sg.Text(key='-INFO-')]
              ]

    window = sg.Window('Multiframe DICOM viewer', layout, resizable=True, finalize=True)

    fig,ax = plt.subplots()
    ax.set_axis_off()
    draw_figure(window['-CANVAS-'].TKCanvas, fig)
    dicom_data = None

    while True:
        event, values = window.read()
        #print(event, values)
        if event in (None, 'Exit'):  # if user closes window or clicks Exit
            break
        if event == '-FOLDER OPEN-':
            ax.clear()
            ax.set_axis_off()
            fig.canvas.draw()
            window['-INFO-'].Update(value='Please be patient while data loads.')
            window.perform_long_operation(lambda: open_series(values['-FOLDER OPEN-']), '-DICOMS LOADED-')
            
        if event == '-DICOMS LOADED-':
            dicom_data, vmin, vmax = values['-DICOMS LOADED-']
            if dicom_data:
                window['-FRAME-'].Update(values=[x for x in range(0, len(dicom_data))], value=0)
                ax.set_title(dicom_data[0].name)
                ax.imshow(get_data(dicom_data[0]), vmin=vmin, vmax=vmax, cmap='gray')
                fig.canvas.draw()
                window['-INFO-'].Update(value='')
            else:
                window['-FRAME-'].Update(values=[0], value=0)
                window['-INFO-'].Update(value='No dicom images found. Check folder selection.')


        if event=='-FRAME-' and dicom_data:
            frameNo = values['-FRAME-']
            ax.clear()
            ax.set_title(dicom_data[frameNo].name)
            ax.set_axis_off()
            ax.imshow(get_data(dicom_data[frameNo]), vmin=vmin, vmax=vmax, cmap='gray')
            fig.canvas.draw()

    window.close()


