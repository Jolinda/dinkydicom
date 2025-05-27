import pathlib
from collections import namedtuple
import configparser

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import FreeSimpleGUI as sg
import pydicom

# todo: deal with multiple series in one folder
# see stability checker for one approach
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
            self.maxpix = 2 ** int(self.datasets[0].ds['BitsStored'].value) - 1
        else:
            self.has_dicoms = False

        self.datasets.sort(key=lambda x: int(x.ds['InstanceNumber'].value))
        self.nfiles = len(self.datasets)

    def show_image(self, ax, fileNo=0, vmin=None, vmax=None, sliceNo=0, mosaic=True, view_axis=0, rotate=0):
        filename = self.datasets[fileNo].path.name
        dataset = self.datasets[fileNo].ds
        if not vmin:
            vmin = self.minpixval
        if not vmax:
            vmax = self.maxpixval
        ax.clear()
        ax.set_title(filename)
        ax.set_axis_off()

        assert len(dataset.pixel_array.shape) < 4
        if len(dataset.pixel_array.shape) == 2:
            data = dataset.pixel_array
        elif mosaic:
            data = mosaify(dataset.pixel_array)
        else:
            #data = dataset.pixel_array[sliceNo, ...]
            data = dataset.pixel_array.take(indices=sliceNo, axis=view_axis)
            for x in range(0, rotate):
                data = np.rot90(data)

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

def main():
    config = configparser.ConfigParser()
    configfile = pathlib.Path.home() / 'settings.ini'
    if configfile.exists():
        config.read(configfile)
    else:
        config['defaults'] = {'dicom_path': pathlib.Path.home(),
                              'save_last_path': True}

    dicom_path = config['defaults']['dicom_path']

    sg.theme('Dark Blue 3')

    layout = [[sg.Text('Dicom folder'),
               sg.Input(key='-FOLDER OPEN-', size=(120, None), enable_events=True),
               sg.FolderBrowse(key='-FOLDER BROWSER-', initial_folder=dicom_path)],
              [sg.Text('File'),
               sg.Spin([0], key='-FILENO-', enable_events=True, auto_size_text=False, size=4,
                       bind_return_key=True), #wrap only in newer sg?
               sg.Text('Frame'),
               sg.Spin([0], key='-FRAMENO-', enable_events=True, auto_size_text=False, size=3),
               sg.Text('Axis'),
               sg.Spin([0], key='-AXIS-', enable_events=True),
               sg.Text('vmin'),
               sg.Slider(key='-VMIN-', orientation = 'h', range=(0, 1000),
                         default_value=0, enable_events=True, expand_x=True),
               sg.Text('vmax'),
               sg.Slider(key='-VMAX-', orientation = 'h', range=(0, 1000),
                         default_value=1000, enable_events=True, expand_x=True),
               sg.Button('Demosaic', key='-DEMOSAIC-', disabled=True),
               sg.Button('Rotate', key='-ROTATE-'),
               sg.Button('Show DICOM file', key='-DICOM TEXT-'), sg.Button('Exit')],
              [sg.Canvas(key='-CANVAS-', expand_x=True, expand_y=True)],
              [sg.Text(key='-INFO-')]
              ]

    window = sg.Window('DinkyDicom Multiframe DICOM Viewer', layout, resizable=True, finalize=True)

    fig,ax = plt.subplots()
    ax.set_axis_off()
    draw_figure(window['-CANVAS-'].TKCanvas, fig)
    dicom_data = None
    mosaic = True
    rotate = 0
    vmin = 0
    vmax = 4096

    while True:
        event, values = window.read()
        if event in (None, 'Exit'):  # if user closes window or clicks Exit
            break
        if event == '-FOLDER OPEN-':
            ax.clear()
            ax.set_axis_off()
            fig.canvas.draw()
            window['-INFO-'].Update(value='Please be patient while data loads.')
            window['-FOLDER BROWSER-'].InitialFolder = values['-FOLDER OPEN-']
            window.perform_long_operation(lambda: DicomSeries(values['-FOLDER OPEN-']), '-DICOMS LOADED-')
            if config['defaults'].getboolean('save_last_path'):
                config['defaults']['dicom_path'] = values['-FOLDER OPEN-']
            
        if event == '-DICOMS LOADED-':
            dicom_data = values['-DICOMS LOADED-']
            if dicom_data.has_dicoms:
                if dicom_data.datasets[0].ds['SOPClassUID'].value == pydicom.uid.EnhancedMRImageStorage:
                    window['-DEMOSAIC-'].Update(disabled=False, text='Demosaic')
                else:
                    window['-DEMOSAIC-'].Update(disabled=True)
                mosaic=True
                fileNo = 0
                frameNo = 0
                rotate = 0
                window['-FILENO-'].Update(values=[x for x in range(0, dicom_data.nfiles)], value=0)
                data_shape = dicom_data.datasets[0].ds.pixel_array.shape
                window['-AXIS-'].Update(values=[x for x in range(0, len(data_shape))], value=0)
                dicom_data.show_image(ax)
                fig.canvas.draw()
                max_range = dicom_data.maxpix
                vmin = dicom_data.minpixval
                vmax = dicom_data.maxpixval
                if vmax == max_range:
                    sg.popup('Brightest pixel is at max range. Image intensity values may be clipped.',
                             title='Warning')
                window['-VMIN-'].Update(value=vmin, range=(0, max_range))
                window['-VMAX-'].Update(value=vmax, range=(0, max_range))

                if dicom_data.nfiles > 1:
                    window['-INFO-'].Update(value=f'{dicom_data.nfiles} files loaded.')
                else:
                    window['-INFO-'].Update(value=f'1 file loaded.')
            else:
                window['-FRAMENO-'].Update(values=[0], value=0)
                window['-FILENO-'].Update(values=[0], value=0)
                window['-INFO-'].Update(value='No dicom images found. Check folder selection.')
                dicom_data = None

        if event == '-FRAMENO-' and dicom_data:
            fileNo = values['-FILENO-']
            frameNo = values['-FRAMENO-']
            axisNo = values['-AXIS-']
            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis=axisNo, rotate=rotate)
            fig.canvas.draw()

        if event == '-FILENO-' and dicom_data:
            if values['-FILENO-'] not in window['-FILENO-'].Values:
                window['-FILENO-'].Update(value=0)
                values['-FILENO-']=0
            fileNo = values['-FILENO-']
            frameNo = values['-FRAMENO-']
            axisNo = values['-AXIS-']
            nslices = dicom_data.datasets[fileNo].ds.pixel_array.shape[axisNo]
            if frameNo >= nslices:
                frameNo = 0
            window['-FRAMENO-'].Update(value=frameNo, values=[x for x in range(0, nslices)])

            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis=axisNo, rotate=rotate)
            fig.canvas.draw()

        if event == '-AXIS-' and dicom_data and not mosaic:
            axisNo = values['-AXIS-']
            fileNo = values['-FILENO-']
            nslices = dicom_data.datasets[fileNo].ds.pixel_array.shape[axisNo]
            frameNo = 0
            window['-FRAMENO-'].Update(value=0, values=[x for x in range(0, nslices)])
            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis=axisNo, rotate=rotate)
            fig.canvas.draw()

        if event == '-ROTATE-' and dicom_data:
            rotate = (rotate + 1) % 4
            fileNo = values['-FILENO-']
            frameNo = values['-FRAMENO-']
            axisNo = values['-AXIS-']
            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis=axisNo, rotate=rotate)
            fig.canvas.draw()

        if event in ['-VMIN-', '-VMAX-'] and dicom_data:
            vmin = values['-VMIN-']
            vmax = values['-VMAX-']
            if event == '-VMIN-' and vmin > vmax:
                vmin = vmax
                window['-VMIN-'].Update(value=vmin)
            if event == '-VMAX-' and vmin > vmax:
                vmax = vmin
                window['-VMAX-'].Update(value=vmax)

            fileNo = values['-FILENO-']
            frameNo = values['-FRAMENO-']
            axisNo = values['-AXIS-']
            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis=axisNo, rotate=rotate)
            fig.canvas.draw()

        if event == '-DEMOSAIC-' and dicom_data:
            mosaic = not mosaic
            vmin = values['-VMIN-']
            vmax = values['-VMAX-']
            if not mosaic:
                fileNo = values['-FILENO-']
                nslices = dicom_data.datasets[fileNo].ds.pixel_array.shape[0]
                window['-FRAMENO-'].Update(values=[x for x in range(0, nslices)], value=0)
                window['-DEMOSAIC-'].Update(text='Mosaic')
            else:
                rotate = 0
                window['-FRAMENO-'].Update(values=[0], value=0)
                window['-DEMOSAIC-'].Update(text='Demosaic')

            fileNo = values['-FILENO-']
            frameNo = values['-FRAMENO-']
            axisNo = values['-AXIS-']
            dicom_data.show_image(ax, fileNo=fileNo, vmin=vmin, vmax=vmax, sliceNo=frameNo, mosaic=mosaic,
                                  view_axis = axisNo, rotate=rotate)
            fig.canvas.draw()

        if event == '-DICOM TEXT-':
            if dicom_data:
                sg.popup_scrolled(dicom_data.datasets[fileNo].ds,
                                  title=dicom_data.datasets[fileNo].path,
                                  font='Courier', modal=False, non_blocking=True)

    window.close()

    with open(configfile, 'w') as f:
        config.write(f)

