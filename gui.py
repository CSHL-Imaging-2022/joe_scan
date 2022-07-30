import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
from superqt import QLabeledDoubleRangeSlider, QLabeledDoubleSlider, QLabeledSlider
from skimage import io
import nidaqmx

from wavegenbase import WaveformGen


class WaveformGUI(QtWidgets.QWidget):
    def __init__(self, devname='auto', sample_rate=20000):
        if devname == 'auto':  # Take the first attached/running NI box
            devname = nidaqmx.system.System.local().devices.device_names[0]

        super(WaveformGUI, self).__init__()
        self.sample_rate = sample_rate
        self.wavegen = WaveformGen(devname=devname, sample_rate=self.sample_rate)

        self.setWindowTitle('Galvo control')
        self.setMinimumSize(1000, 800)

        hbox = QtWidgets.QHBoxLayout()
        self.setLayout(hbox)

        def slider_label(text):
            """Helper function for making slider labels"""
            label = QtWidgets.QLabel(text, self)
            label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            label.setMinimumWidth(80)
            return label

        vbox_control = QtWidgets.QVBoxLayout()
        hbox.addLayout(vbox_control)
        hbox.addSpacing(10)
        # vbox_control.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        # vbox_control.setSizeConstraint(500)

        self.startstopbutton = QtWidgets.QPushButton("Start")
        self.startstopbutton.setFixedHeight(85)
        vbox_control.addWidget(self.startstopbutton)
        vbox_control.addSpacing(10)
        # self.startstopbutton.setMaximumWidth(300)

        self.zerobutton = QtWidgets.QPushButton("Zero galvos")
        self.zerobutton.setFixedHeight(45)
        vbox_control.addWidget(self.zerobutton)
        vbox_control.addSpacing(15)
        # self.zerobutton.setMaximumWidth(300)

        self.x_amp = QLabeledDoubleSlider(QtCore.Qt.Horizontal)
        self.x_amp.setRange(0.1, 5)
        self.x_amp.setValue(1)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("X amp (v)"))
        vbox_control.addWidget(self.x_amp)
        vbox_control.addSpacing(8)

        self.x_offset = QLabeledDoubleSlider(QtCore.Qt.Horizontal)
        self.x_offset.setRange(-2, 2)
        self.x_offset.setValue(0)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("X offset (v)"))
        vbox_control.addWidget(self.x_offset)
        vbox_control.addSpacing(10)

        self.y_amp = QLabeledDoubleSlider(QtCore.Qt.Horizontal)
        self.y_amp.setRange(0.1, 5)
        self.y_amp.setValue(1)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("Y amp (v)"))
        vbox_control.addWidget(self.y_amp)
        vbox_control.addSpacing(8)

        self.y_offset = QLabeledDoubleSlider(QtCore.Qt.Horizontal)
        self.y_offset.setRange(-2, 2)
        self.y_offset.setValue(0)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("Y offset (v)"))
        vbox_control.addWidget(self.y_offset)
        vbox_control.addSpacing(10)

        self.x_pix = QLabeledSlider(QtCore.Qt.Horizontal)
        self.x_pix.setRange(50, 500)
        self.x_pix.setValue(100)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("# X Pixels"))
        vbox_control.addWidget(self.x_pix)
        vbox_control.addSpacing(8)

        self.y_pix_lbl = QtWidgets.QLabel()
        self.y_pix_lbl.setText("# Y Pixels:")
        vbox_control.addWidget(self.y_pix_lbl)
        vbox_control.addSpacing(8)

        self.samples_per_pixel = QLabeledSlider(QtCore.Qt.Horizontal)
        self.samples_per_pixel.setRange(1, 20)
        self.samples_per_pixel.setValue(1)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        vbox_control.addWidget(slider_label("Samples per pixel"))
        vbox_control.addWidget(self.samples_per_pixel)
        vbox_control.addSpacing(8)

        self.fps = QtWidgets.QLabel()
        self.fps.setText("Frames per second: ?")
        vbox_control.addWidget(self.fps)
        vbox_control.addSpacing(10)

        vbox_images = QtWidgets.QVBoxLayout()
        hbox.addLayout(vbox_images)
        graphics = pg.ImageView()  # QtWidgets.QGraphicsView()
        graphics.show()
        graphics.setImage(np.random.random((200, 100)))
        self.wavegen.reading_image_callback = lambda x: graphics.setImage(x, autoLevels=False, autoHistogramRange=False, levelMode='mono')
        graphics.view.setAspectLocked(True)
        # graphics.view.setRange(xRange=[0, 100], yRange=[0, 100], padding=0)
        graphics.ui.roiBtn.hide()
        graphics.ui.menuBtn.hide()
        graphics.getHistogramWidget().setHistogramRange(-20, 20)
        graphics.setLevels(-15, 15)
        graphics.setMinimumWidth(600)
        graphics.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        vbox_images.addWidget(graphics)

        self.savebutton = QtWidgets.QPushButton("Save last acquisition")
        vbox_images.addWidget(self.savebutton)

        # self.plotwidget = pg.PlotWidget()
        # vbox.addWidget(self.plotwidget)

        # self.plotwidget.addLegend(offset=(0., .6))
        # self.plotwidget.setYRange(-10, 10)
        # self.plotcurvex = pg.PlotCurveItem(name="X", pen=pg.mkPen('g', width=3))
        # self.plotwidget.addItem(self.plotcurvex)
        # self.plotcurvey = pg.PlotCurveItem(name="Y", pen=pg.mkPen('b', width=3))
        # self.plotwidget.addItem(self.plotcurvey)
        # self.plotcurveamp = pg.PlotCurveItem(name="Amplitude", pen=pg.mkPen('r', width=1))
        # self.plotwidget.addItem(self.plotcurveamp)
        #
        # self.plotwidget.setLabel('bottom', 'time (sec)')


        self.state_toggles_widgets = [self.x_amp, self.x_offset, self.y_amp, self.y_offset, self.x_pix, self.samples_per_pixel, self.savebutton]

        for slider in [self.x_amp, self.x_offset, self.y_amp, self.y_offset, self.x_pix, self.samples_per_pixel]:
            slider.valueChanged.connect(self.update)
        self.startstopbutton.clicked.connect(self.startstop)
        self.zerobutton.clicked.connect(self.wavegen.zero_output)
        self.savebutton.clicked.connect(self.save)

        self.update()

        self.setGeometry(50, 50, 1400, 800)
        self.show()
        self.started = False
        self.lastacqframes = []

    def update(self):
        self.wavegen.x_amp = self.x_amp.value()
        self.wavegen.x_offset = self.x_offset.value()
        self.wavegen.y_amp = self.y_amp.value()
        self.wavegen.y_offset = self.y_offset.value()
        self.wavegen.pixels_x = self.x_pix.value()
        self.wavegen.samples_per_pixel = self.samples_per_pixel.value()
        self.y_pix_lbl.setText(f"# Y Pixels: {self.wavegen.pixels_y}")
        self.fps.setText(f"Frames per second: {self.wavegen.fps:0.2f}")

    def startstop(self):
        if self.started:
            self.stop()
        else:
            self.start()

    def start(self):
        self.started = True
        self.startstopbutton.setText("Scanning")
        self.startstopbutton.setStyleSheet("background-color: red")
        [w.setDisabled(True) for w in self.state_toggles_widgets]
        self.wavegen.start()

    def stop(self):
        self.started = False
        self.startstopbutton.setText("Start")
        self.startstopbutton.setStyleSheet("")
        [w.setDisabled(False) for w in self.state_toggles_widgets]
        self.lastacqframes = self.wavegen.frames
        self.wavegen.stop()
        self.wavegen.close()

    # def closeEvent(self, event):
    #     # self.wavegen.close()
    #     event.accept()

    def save(self):
        if self.lastacqframes:
            filename = QtWidgets.QFileDialog.getSaveFileName(filter="Tif files (*.tif)")[0]
            io.imsave(filename, np.stack(self.lastacqframes))
            # msg = QtWidgets.QMessageBox()
            # msg.setIcon(QtWidgets.QMessageBox.Information)
            # msg.setText(f"The last acquisition has been saved to: <b> {filename}</b>")
            # msg.setWindowTitle("Save successful")
            # msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            # msg.exec_()
            print(f"Saved last acq as {filename}")
        else:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Information)
            msg.setText(f"Please acquire data before trying to save!")
            msg.setWindowTitle("No data")
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msg.exec_()


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('Galvo control')
    wg = WaveformGUI(devname='auto')
    # Makes ctrl-c work, but non-zero exit code
    # import signal
    # signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(app.exec_())
