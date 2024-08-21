import sys
from itertools import chain

import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QCheckBox, QFileDialog
from PyQt5.QtCore import Qt
from scipy.signal import freqz_zpk, lfilter
import numpy as np
import matplotlib.pyplot as plt


class ZPlaneSignalFilter(QWidget):
    def __init__(self, unit_circle_w, mag_res_w, phase_res_w, checkbox):
        super().__init__()
        self.delete_flag = False  # Flag to control deletion or creation
        self.conjugate_flag = False  # Flag to determine if conjugate plotting is enabled
        self.unit_circle_w = unit_circle_w
        self.mag_res_w = mag_res_w
        self.phase_res_w = phase_res_w
        self.reflect_checkbox = checkbox
        self.init_ui()

    def init_ui(self):

        # Create the plot widget
        self.plot_widget = self.unit_circle_w
        self.plot_widget.setAspectLocked()
        self.plot_widget.showGrid(x=False, y=False)
        self.plot_widget.setBackground((25, 35, 45))
        # Draw the unit circle as a CircleROI
        self.unit_circle = pg.CircleROI([-1, -1], size=[2, 2], movable=False, pen=(0, 0, 255))
        self.plot_widget.addItem(self.unit_circle)

        # Draw x-axis and y-axis at the center of the circle
        self.x_axis = pg.InfiniteLine(pos=0, angle=0, pen=(255, 0, 0), movable=False)
        self.y_axis = pg.InfiniteLine(pos=0, angle=90, pen=(0, 255, 0), movable=False)
        self.plot_widget.addItem(self.x_axis)
        self.plot_widget.addItem(self.y_axis)

        # Initialize lists for zeros, poles, and their corresponding items
        self.zeros = []
        self.poles = []
        self.zero_items = []
        self.pole_items = []

        # Lists for conjugate zeros and poles
        self.zerosf = []
        self.polesf = []
        self.zero_itemsf = []
        self.pole_itemsf = []

        # Lists to store pairs of items for conjugate plotting
        self.list_pairs_poles = []
        self.list_pairs_zeros = []

        # Connect signals
        self.plot_widget.scene().sigMouseClicked.connect(self.on_click)
        self.plot_widget.scene().sigMouseClicked.connect(self.clear_zero_or_pole)

        # Initialize signal data
        self.t = None
        self.x = None

    def zero_moved(self, zero_addr, e):
        for z in self.list_pairs_zeros:
            if id(z[0]) == zero_addr:
                z[1].setPos((e.pos().x(), -1 * e.pos().y()))
            elif id(z[1]) == zero_addr:
                z[0].setPos((e.pos().x(), -1 * e.pos().y()))

    def pole_moved(self, pole_addr, e):
        for z in self.list_pairs_poles:
            if id(z[0]) == pole_addr:
                z[1].setPos((e.pos().x(), -1 * e.pos().y()))
            elif id(z[1]) == pole_addr:
                z[0].setPos((e.pos().x(), -1 * e.pos().y()))

    def update_zero_position(self, zero_item, e):
        index = self.zero_items.index(zero_item)
        self.zeros[index] = (e.pos().x(), -1 * e.pos().y())
        self.plot_frequency_response()

    def update_pole_position(self, pole_item, e):
        index = self.pole_items.index(pole_item)
        self.poles[index] = (e.pos().x(), -1 * e.pos().y())
        self.plot_frequency_response()

    def on_click(self, event):
        pos = self.plot_widget.getViewBox().mapSceneToView(event.scenePos())

        if self.reflect_checkbox.isChecked():
            if event.button() == 1:  # Left mouse button for poles
                self.poles.append((pos.x(), pos.y()))
                self.plot_pole(pos.x(), pos.y())

            elif event.button() == 2:  # Right mouse button for zeros
                self.zeros.append((pos.x(), pos.y()))
                self.plot_zero(pos.x(), pos.y())

        elif not self.reflect_checkbox.isChecked():
            # Add a new point at the clicked position
            if event.button() == 1:  # Left mouse button for poles
                self.poles.append((pos.x(), pos.y()))
                self.plot_pole(pos.x(), pos.y())

            elif event.button() == 2:  # Right mouse button for zeros
                self.zeros.append((pos.x(), pos.y()))
                self.plot_zero(pos.x(), pos.y())
        self.plot_frequency_response()

    def clear_zero_or_pole(self, event):
        if event.button() == Qt.MiddleButton:
            pos = self.plot_widget.getViewBox().mapSceneToView(event.scenePos())

            def find_nearest(coords_list, target):
                # Calculate the distances between each coordinate in the list and the target
                distances = [np.linalg.norm(np.array(coord) - np.array(target)) for coord in coords_list]
                # Find the index of the coordinate with the minimum distance
                min_index = np.argmin(distances)
                return min_index

            # Check if the pulley click is near any zero or pole
            for zero_item in self.zero_items:
                if np.linalg.norm(np.array(zero_item.pos()) - np.array([pos.x(), pos.y()])) < 0.1:
                    self.plot_widget.removeItem(zero_item)
                    zero_conj = None
                    for z in self.list_pairs_zeros:
                        if id(z[0]) == id(zero_item):
                            zero_conj = z[1]
                            break
                        elif id(z[1]) == id(zero_item):
                            zero_conj = z[0]
                            break
                    if zero_conj is not None:
                        self.plot_widget.removeItem(zero_conj)
                        index_conj = find_nearest(self.zerosf, (pos.x(), -pos.y()))
                        self.zero_itemsf.remove(zero_conj)
                        self.zerosf.pop(index_conj)
                    index = find_nearest(self.zeros, (pos.x(), pos.y()))

                    self.zero_items.remove(zero_item)

                    self.zeros.pop(index)

                    break

            try:
                for pole_item in self.pole_items:
                    if np.linalg.norm(np.array(pole_item.pos()) - np.array([pos.x(), pos.y()])) < 0.1:
                        self.plot_widget.removeItem(pole_item)
                        pole_conj = None
                        for z in self.list_pairs_poles:
                            if id(z[0]) == id(pole_item):
                                pole_conj = z[1]
                                break
                            elif id(z[1]) == id(pole_item):
                                pole_conj = z[0]
                                break
                        if pole_conj is not None:
                            self.plot_widget.removeItem(pole_conj)
                            index_conj = find_nearest(self.polesf, (pos.x(), -pos.y()))
                            self.pole_itemsf.remove(pole_conj)
                            self.polesf.pop(index_conj)
                        index = find_nearest(self.poles, (pos.x(), pos.y()))
                        self.pole_items.remove(pole_item)
                        self.poles.pop(index)
                        break
            except ValueError:
                print(f"Coordinates {pos.x(), pos.y()} not found in the list of poles.")

            self.plot_frequency_response()

    def clear_zeros_and_poles(self):
        for zero_item in self.zero_items:
            self.plot_widget.removeItem(zero_item)
        for zero_itemf in self.zero_itemsf:
            self.plot_widget.removeItem(zero_itemf)
        self.zero_items = []
        self.zeros = []
        self.zerosf = []
        self.zero_itemsf = []

        for pole_item in self.pole_items:
            self.plot_widget.removeItem(pole_item)
        for pole_itemf in self.pole_itemsf:
            self.plot_widget.removeItem(pole_itemf)
        self.pole_items = []
        self.poles = []
        self.polesf = []
        self.pole_itemsf = []
        self.mag_res_w.clear()
        self.phase_res_w.clear()

    def clear_poles(self):
        for pole_item in self.pole_items:
            self.plot_widget.removeItem(pole_item)
        for pole_itemf in self.pole_itemsf:
            self.plot_widget.removeItem(pole_itemf)
        self.pole_items = []
        self.poles = []
        self.polesf = []
        self.pole_itemsf = []
        self.plot_frequency_response()

    def clear_zeros(self):
        for zero_item in self.zero_items:
            self.plot_widget.removeItem(zero_item)
        for zero_itemf in self.zero_itemsf:
            self.plot_widget.removeItem(zero_itemf)
        self.zero_items = []
        self.zeros = []
        self.zerosf = []
        self.zero_itemsf = []
        self.plot_frequency_response()

    def plot_pole(self, x, y):
        target_pole = pg.TargetItem(pos=[x, y], size=20, symbol='x', pen='w', brush='w', movable=True)
        self.pole_items.append(target_pole)
        self.plot_widget.addItem(target_pole)

        target_pole.sigPositionChanged.connect(lambda e: self.pole_moved(id(target_pole), e))
        target_pole.sigPositionChanged.connect(lambda e: self.update_pole_position(target_pole, e))

        if self.reflect_checkbox.isChecked():
            reflected_y = -y
            self.polesf.append((x, reflected_y))
            target_reflected_pole = pg.TargetItem(
                pos=[x, reflected_y], size=20, symbol='x', pen='g', brush='g', movable=False)
            self.pole_itemsf.append(target_reflected_pole)
            self.plot_widget.addItem(target_reflected_pole)
            self.list_pairs_poles = [(target_pole, target_reflected_pole)]

    def plot_zero(self, x, y):
        target_zero = pg.TargetItem(pos=[x, y], size=20, symbol='o', pen='w', brush='w', movable=True)
        self.zero_items.append(target_zero)
        self.plot_widget.addItem(target_zero)

        target_zero.sigPositionChanged.connect(lambda e: self.zero_moved(id(target_zero), e))
        target_zero.sigPositionChanged.connect(lambda e: self.update_zero_position(target_zero, e))

        if self.reflect_checkbox.isChecked():
            reflected_y = -y
            self.zerosf.append((x, reflected_y))
            target_reflected_zero = pg.TargetItem(
                pos=[x, reflected_y], size=20, symbol='o', pen='g', brush='g', movable=False)
            self.zero_itemsf.append(target_reflected_zero)
            self.plot_widget.addItem(target_reflected_zero)
            self.list_pairs_zeros = [(target_zero, target_reflected_zero)]

    def plot_frequency_response(self):
        zeros = [complex(z[0], z[1]) for z in self.zeros]
        poles = [complex(p[0], p[1]) for p in self.poles]
        return self.plot_response(zeros, poles)

    def plot_response(self, zeros, poles):
        # Generate frequencies for the frequency range
        frequencies, response = freqz_zpk(zeros, poles, k=1)

        # Plot the magnitude response
        # plt.figure(figsize=(10, 5))
        # plt.subplot(2, 1, 1)
        magnitude = np.abs(response)
        if np.any(np.iscomplex(magnitude)):
            magnitude = np.abs(response.astype(float))  # Cast to float to remove complex part
        # plt.plot(frequencies, magnitude)
        plot = pg.PlotDataItem(frequencies, magnitude)
        self.mag_res_w.clear()
        self.mag_res_w.addItem(plot)

        phase = np.angle(response)
        if np.any(np.iscomplex(phase)):
            phase = np.angle(response.astype(float))  # Cast to float to remove complex part
        plot = pg.PlotDataItem(frequencies, phase)
        self.phase_res_w.clear()
        self.phase_res_w.addItem(plot)
        return frequencies, phase

    def load_signal_from_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly

        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV Signal File", "", "CSV Files (*.csv);;All Files (*)",
                                                   options=options)

        if file_name:
            data = np.loadtxt(file_name, delimiter=',')
            # self.t = data[0,: ]
            self.x = data[0, :]
            # self.clear_zeros_and_poles()

    # def show_original_and_filtered_signals(self):
    #     pass
    #     # if self.t is not None and self.x is not None:
    #     #     b, a = freqz_zpk(self.zeros, self.poles, k=1)
    #     # print(b)
    #     # print()
    #     # b=b[:,1]
    #     # a=a[:,1]
    #
    #     print(b)
    #     # print(b)
    #
    #     y_filtered = lfilter(b, a, self.x)
    #     # print(self.x)
    #
    #     plt.figure(figsize=(10, 6))
    #     plt.plot(self.t, np.real(self.x), label='Original Signal (Real)')
    #     plt.plot(self.t, np.real(y_filtered), label='Filtered Signal (Real)')
    #     plt.xlabel('Time')
    #     plt.ylabel('Amplitude')
    #     plt.legend()
    #     plt.show()
    #     # print(self.x)
    # Apply the digital filter
    # output_signal = digital_filter(input_signal, zeros, poles)
    #
    # # Plot the original and filtered signals
    # plt.figure(figsize=(10, 6))
    # plt.plot(input_signal, label='Original Signal', marker='o')
    # plt.plot(output_signal, label='Filtered Signal', marker='x')
    # plt.xlabel('Sample Index')
    # plt.ylabel('Amplitude')
    # plt.title('Original and Filtered Signals')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    # def digital_filter(self):
    # # Extract coefficients from zeros and poles
    # # print(self.zeros)
    # zero_flatten = list(chain(*self.zeros))
    # # print(zero_flatten)
    # pole_flatten = list(chain(*self.poles))
    # b = np.poly(zero_flatten)
    # a = np.poly(pole_flatten)

    # # Initialize state variables
    # x_history = np.zeros(len(b))

    # if np.isscalar(a):  # Check if 'a' is a scalar (float)
    #     y_history = np.zeros(0)
    # else:
    #     y_history = np.zeros(len(a) - 1)

    # # Apply the filter
    # output_signal = []
    # for sample in self.x:
    #     # Update state variables
    #     x_history[1:] = x_history[:-1]
    #     x_history[0] = sample

    #     # Calculate output using the difference equation
    #     y = np.dot(b, x_history)

    #     if not np.isscalar(a):
    #         y -= np.dot(a[1:], y_history)

    #         # Update y_history
    #         y_history[1:] = y_history[:-1]
    #         y_history[0] = y

    # output_signal.append(y)

    # # Plot the original and filtered signals
    # plt.figure(figsize=(10, 6))
    # plt.plot(self.x, label='Original Signal')
    # plt.plot(output_signal, label='Filtered Signal')
    # plt.xlabel('Sample Index')
    # plt.ylabel('Amplitude')
    # plt.title('Original and Filtered Signals')
    # plt.legend()
    # plt.grid(True)
    # plt.show()

    # return output_signal

