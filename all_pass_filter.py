import random

import numpy as np
import pyqtgraph as pg
from scipy.signal import freqz, tf2zpk
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class AllPassFilterFeature(object):
    def __init__(self, filters=None, phase_w=None, poles_zeros_w=None):
        self.phase_scene = phase_w if phase_w is not None else pg.PlotWidget()
        self.mag_scene = pg.PlotWidget()
        self.zeros_poles_scene = poles_zeros_w if poles_zeros_w is not None else pg.PlotWidget()
        self.all_pass_filters = filters if filters is not None else []
        self.phase_response = 0

    def get_scene(self):
        self.phase_scene.clear()
        self.mag_scene.clear()
        self.zeros_poles_scene.clear()
        phase_response = []
        freqs = 0
        for filter in self.all_pass_filters:
            mag, _ = filter.get_frequency_response_plots()
            freqs, phase = filter.calculate_phase_response()
            poles, zeros, circle = filter.get_zeros_poles_plot()
            phase_response.append(phase)
            self.mag_scene.addItem(mag)
            self.zeros_poles_scene.addItem(poles)
            self.zeros_poles_scene.addItem(zeros)
            self.zeros_poles_scene.addItem(circle)
            self.zeros_poles_scene.setBackground((25, 35, 45))
            self.x_axis = pg.InfiniteLine(pos=0, angle=0, pen=(255, 0, 0), movable=False)
            self.y_axis = pg.InfiniteLine(pos=0, angle=90, pen=(0, 255, 0), movable=False)
            self.zeros_poles_scene.addItem(self.x_axis)
            self.zeros_poles_scene.addItem(self.y_axis)
        phase_response = np.sum(np.array(phase_response), axis=0)
        self.phase_response = phase_response
        phase_plot = pg.PlotDataItem(0.5 * freqs / np.pi, phase_response)
        self.phase_scene.addItem(phase_plot)

        return self.phase_scene, self.mag_scene, self.zeros_poles_scene

    def get_corrected_phase_plot(self, filter):
        freqs, phase = filter.plot_frequency_response()
        filter.phase_res_w.clear()
        corrected_phase = phase + self.phase_response
        return pg.PlotDataItem(freqs, corrected_phase)


class AllPassFilter:
    def __init__(self, a):
        self.a = a
        self.zeros, self.poles, self.gain = tf2zpk([-np.conjugate(a), 1], [1, -a])
        self.freq_response_plot = self.get_frequency_response_plots()
        self.zeros_poles_plot = self.get_zeros_poles_plot()
        self.frequencies, self.phase_values = self.calculate_phase_response()

    def transfer_function(self, z):
        return (z ** -1 - self.a) / (1 - self.a * z ** -1)

    def get_freq_response(self):
        # Frequency response
        frequencies, response = freqz([-np.conjugate(self.a), 1], [1, -self.a], worN=512)
        return frequencies, response

    def get_frequency_response_plots(self):
        # Frequency response
        frequencies, response = freqz([-np.conjugate(self.a), 1], [1, -self.a], worN=512)

        # Plot magnitude response

        mag_plot = pg.PlotDataItem(0.5 * frequencies / np.pi, np.abs(response))
        # Plot phase response
        phase_plot = pg.PlotDataItem(0.5 * frequencies / np.pi, np.angle(response))

        return mag_plot, phase_plot

    def get_zeros(self):
        return self.zeros

    def get_poles(self):
        return self.poles

    def get_zeros_poles_plot(self):
        zeros_plot = pg.PlotDataItem(self.zeros.real, self.zeros.imag, size=15, symbol='o', pen='g', brush='g')
        poles_plot = pg.PlotDataItem(self.poles.real, self.poles.imag, size=15, symbol='x', pen='w', brush='w')
        # Plot unit circle
        theta = np.linspace(0, 2 * np.pi, 100)
        x_circle = np.cos(theta)
        y_circle = np.sin(theta)
        # win.plot(x_circle, y_circle, pen=pg.mkPen('g', width=1.5), name='Unit Circle')
        circle = pg.PlotDataItem(x_circle, y_circle, pen=pg.mkPen((0, 0, 255), width=1.5))

        return poles_plot, zeros_plot, circle

    def calculate_phase_response(self):
        # Calculate phase response at different frequencies
        frequencies, response = freqz([-np.conjugate(self.a), 1], [1, -self.a], worN=512)
        phase_values = np.angle(response)
        return 0.5 * frequencies / np.pi, phase_values


class OnlineFilter(object):
    def __init__(self, signal, filter, all_pass_filters=None):
        self._signal = signal
        self._filter = filter
        self._all_pass_filters = all_pass_filters if all_pass_filters is not None else []
        self._current_sample_index = -1
        self._current_sample = None
        self._current_filtered_sample = 0
        self._filtered_signal = []
        self._zeros = []
        self._poles = []
        self._nzeros = 0
        self._npoles = 0
        self._H_numerator_poly = []
        self._H_denominator_poly = []
        self._is_consumed = True if len(self.signal) == 0 else False
        self._inputs = []
        self._outputs = []

    @property
    def is_consumed(self):
        if len(self.signal) == 0:
            self._is_consumed = True
            return True
        if self.current_sample_index >= len(self.signal) - 1:
            self.is_consumed = True
            return True
        self._is_consumed = False
        return self._is_consumed

    @is_consumed.setter
    def is_consumed(self, value):
        self._is_consumed = value

    @property
    def signal(self):
        return self._signal

    @signal.setter
    def signal(self, value):
        self._signal = value

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        self._filter = value

    @property
    def all_pass_filters(self):
        return self._all_pass_filters

    @all_pass_filters.setter
    def all_pass_filters(self, value):
        self._all_pass_filters = value

    @property
    def current_sample_index(self):
        return self._current_sample_index

    @current_sample_index.setter
    def current_sample_index(self, value):
        self._current_sample_index = value

    @property
    def current_sample(self):
        self._current_sample = self.signal[self.current_sample_index]
        return self._current_sample

    @current_sample.setter
    def current_sample(self, value):
        self._current_sample = value

    @property
    def current_filtered_sample(self):
        return self._current_filtered_sample

    @current_filtered_sample.setter
    def current_filtered_sample(self, value):
        self._current_filtered_sample = value

    @property
    def filtered_signal(self):
        return self._filtered_signal

    @filtered_signal.setter
    def filtered_signal(self, value):
        self._filtered_signal = value

    @property
    def zeros(self):
        all_pass_zeros = np.array([])
        filter_zeros = np.array([])
        for filter in self.all_pass_filters:
            all_pass_zeros = np.append(all_pass_zeros, filter.get_zeros())
        filter_zeros = self.filter.zeros + self.filter.zerosf
        filter_zeros = np.array(filter_zeros)
        if len(filter_zeros) > 0:
            filter_zeros = filter_zeros.transpose()[0] + 1j * filter_zeros.transpose()[1]
        self._zeros = np.concatenate((all_pass_zeros, filter_zeros))
        return self._zeros

    @zeros.setter
    def zeros(self, value):
        self._zeros = value

    @property
    def poles(self):
        all_pass_poles = np.array([])
        filter_poles = np.array([])
        for filter in self.all_pass_filters:
            all_pass_poles = np.append(all_pass_poles, filter.get_poles())
        filter_poles = self.filter.poles + self.filter.polesf
        filter_poles = np.array(filter_poles)
        if len(filter_poles) > 0:
            filter_poles = filter_poles.transpose()[0] + 1j * filter_poles.transpose()[1]
        self._poles = np.concatenate((all_pass_poles, filter_poles))
        return self._poles

    @poles.setter
    def poles(self, value):
        self._poles = value

    @property
    def nzeros(self):
        n = len(self.zeros)
        self._nzeros = n
        return self._nzeros

    @nzeros.setter
    def nzeros(self, value):
        self._nzeros = value

    @property
    def npoles(self):
        n = len(self.poles)
        self._npoles = n
        return self._npoles

    @npoles.setter
    def npoles(self, value):
        self._npoles = value

    @property
    def H_numerator_poly(self):
        if self.nzeros != 0:
            self._H_numerator_poly = np.poly(self.zeros)
        else:
            self._H_numerator_poly = np.array([1])
        return self._H_numerator_poly

    @H_numerator_poly.setter
    def H_numerator_poly(self, value):
        self._H_numerator_poly = value

    @property
    def H_denominator_poly(self):
        if self.npoles != 0:
            self._H_denominator_poly = np.poly(self.poles)
        else:
            self._H_denominator_poly = np.array([1])
        return self._H_denominator_poly

    @H_denominator_poly.setter
    def H_denominator_poly(self, value):
        self._H_denominator_poly = value

    def apply_filter(self):
        if not self.is_consumed:
            self.current_sample_index += 1
            # Handle right-hand side of the difference equation

            while len(self._inputs) >= self.nzeros + 1 and len(self._inputs) != 0:
                self._inputs.pop()
            self._inputs.insert(0, self.current_sample)
            # zero padding for the inputs
            while len(self._inputs) < self.nzeros + 1:
                self._inputs.append(0)
            wighted_input = np.dot(np.array(self._inputs), self.H_numerator_poly)

            # Handle left-hand side of the difference equation
            while len(self._outputs) >= self.npoles and len(self._outputs) != 0:
                self._outputs.pop()

            self._outputs.insert(0, self.current_filtered_sample)
            # zero padding for the inputs
            while len(self._outputs) < self.npoles:
                self._outputs.append(0)
            wighted_output = np.dot(np.array(self._outputs),
                                    self.H_denominator_poly[1:] if len(self.H_denominator_poly[1:]) != 0 else [0])

            leading_coefficient = self.H_denominator_poly[0]
            self.current_filtered_sample = (wighted_input - wighted_output) / leading_coefficient
            self.current_filtered_sample = self.current_filtered_sample.real if type(
                self.current_filtered_sample) == np.complex128 else self.current_filtered_sample
            self.filtered_signal.append(self.current_filtered_sample)

    def reset(self):
        self._current_sample_index = -1
        self._current_sample = None
        self._current_filtered_sample = 0
        self._filtered_signal = []
        self._H_numerator_poly = []
        self._H_denominator_poly = []
        self._is_consumed = True if len(self.signal) == 0 else False
        self._inputs = []
        self._outputs = []

        self.all_pass_filters = []

