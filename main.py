import pathlib
from collections import namedtuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
import PySimpleGUI as sg
import pydicom

# todo: message while data loads. Does not work currently; may need threads
# todo: user change vmin, vmax
DicomDataset = namedtuple('DicomDataset', ['path', 'ds'])
class DicomSeries:
    def __init__(self, foldername):
        self.folderpath = pathlib.Path(foldername)
        self.datasets = [DicomDataset(x, pydicom.dcmread(x)) for x in self.folderpath.glob('*')
                         if x.is_file() and pydicom.misc.is_dicom(x)]

        if self.datasets:
            self.has_dicoms = True
            self.minpixval = min([x.ds['SmallestImagePixelValue'].value for x in self.datasets])
            self.maxpixval = max([x.ds['LargestImagePixelValue'].value for x in self.datasets])
            self.maxpix = 2 ** int(self.datasets[0].ds['BitsStored'].value)
        else:
            self.has_dicoms = False

        self.datasets.sort(key=lambda x: int(x.ds['InstanceNumber'].value))
        self.nfiles = len(self.datasets)

    def show_image(self, ax, frameNo=0, vmin=None, vmax=None):
        filename = self.datasets[frameNo].path.name
        dataset = self.datasets[frameNo].ds
        if not vmin:
            vmin = self.minpixval
        if not vmax:
            vmax = self.maxpixval
        ax.clear()
        ax.set_title(filename)
        ax.set_axis_off()
        data=mosaify(dataset.pixel_array)
        ax.imshow(data, vmin=vmin, vmax=vmax, cmap='gray')

def mosaify(data):
    if len(data.shape) < 3:
        return data
    ndown = int(np.floor(np.sqrt(data.shape[0])))
    nacross = int(np.ceil(data.shape[0] / ndown))
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

    layout = [[sg.Text('Dicom folder'),
               sg.Input(key='-FOLDER OPEN-', size=(120, None), enable_events=True),
               sg.FolderBrowse(key='-FOLDER BROWSER-', initial_folder=dicom_path)],
              [sg.Text('Frame'), sg.Spin([0], key='-FRAME-', enable_events=True),
               sg.Text('vmin'),
               sg.Slider(key='-VMIN-', orientation = 'h', range=(0, 1000),
                         default_value=0, enable_events=True, expand_x=True),
               sg.Text('vmax'),
               sg.Slider(key='-VMAX-', orientation = 'h', range=(0, 1000),
                         default_value=1000, enable_events=True, expand_x=True),
               sg.Button('Show DICOM file', key='-DICOM TEXT-'), sg.Button('Exit')],
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
            window['-FOLDER BROWSER-'].InitialFolder = values['-FOLDER OPEN-']
            window.perform_long_operation(lambda: DicomSeries(values['-FOLDER OPEN-']), '-DICOMS LOADED-')
            
        if event == '-DICOMS LOADED-':
            dicom_data = values['-DICOMS LOADED-']
            if dicom_data.has_dicoms:
                window['-FRAME-'].Update(values=[x for x in range(0, dicom_data.nfiles)], value=0)
                dicom_data.show_image(ax)
                fig.canvas.draw()
                max_range = dicom_data.maxpix
                window['-VMIN-'].Update(value=dicom_data.minpixval, range=(0, max_range))
                window['-VMAX-'].Update(value=dicom_data.maxpixval, range=(0, max_range))

                if dicom_data.nfiles > 1:
                    window['-INFO-'].Update(value=f'{dicom_data.nfiles} files loaded.')
                else:
                    window['-INFO-'].Update(value=f'1 file loaded.')
            else:
                window['-FRAME-'].Update(values=[0], value=0)
                window['-INFO-'].Update(value='No dicom images found. Check folder selection.')
                dicom_data = None


        if event in ['-FRAME-', '-VMIN-', '-VMAX-'] and dicom_data:
            frameNo = values['-FRAME-']
            vmin = values['-VMIN-']
            vmax = values['-VMAX-']
            if event == '-VMIN-' and vmin > vmax:
                vmin = vmax
                window['-VMIN-'].Update(value=vmin)
            if event == '-VMAX-' and vmin > vmax:
                vmax = vmin
                window['-VMAX-'].Update(value=vmax)

            dicom_data.show_image(ax, frameNo=frameNo, vmin=vmin, vmax=vmax)
            fig.canvas.draw()

        if event == '-DICOM TEXT-':
            if dicom_data:
                frameNo = values['-FRAME-']
                sg.popup_scrolled(dicom_data.datasets[frameNo].ds,
                                  title=dicom_data.datasets[frameNo].path,
                                  font='Courier', modal=False, non_blocking=True)


    window.close()


