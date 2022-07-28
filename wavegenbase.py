import nidaqmx
import numpy as np
from nidaqmx import stream_readers, stream_writers
from scipy.ndimage import gaussian_filter1d

from matplotlib import pyplot as plt


class WaveformGen:
    def __init__(self, devname='Dev2', sample_rate=20000, loopback_debug=False):
        self.devname = devname
        device = nidaqmx.system.Device(devname)
        print(f"Connecting to {devname}: {device.product_type}")
        assert device.ao_min_rate <= sample_rate <= device.ao_max_rate
        self.sample_rate = sample_rate

        # Set initial params
        self.x_offset = 0
        self.x_amp = 2
        self.y_offset = 0
        self.y_amp = 1
        # self.tilt = 0

        self.samples_per_pixel = 1
        self.pixels_x = 100
        # self.aspect_ratio = 1  # square pixels for now

        # refresh_rate_hz = self.fps  # Hz, approx how often the NI board is serviced
        self.buffer_oversize = 6  # fold, how much bigger is the buffer than one 'refresh' worth

        # AI params
        self.ai_channels = ['/ai0']  # '/ai1'
        self.ai_args = {'min_val': -10,
                        'max_val': 10,
                        'terminal_config': nidaqmx.constants.TerminalConfiguration.RSE}
        if loopback_debug:
            # loopback AO test
            self.ai_channels = ['/_ao0_vs_aognd', '/_ao1_vs_aognd']
            self.ai_args = {'min_val': -5,
                            'max_val': 5,
                            'terminal_config': nidaqmx.constants.TerminalConfiguration.BAL_DIFF}
        self.reader = None
        self.ai_task = None

        # AO params
        self.ao_channels = ['/ao0', '/ao1']
        self.ao_args = {'min_val': -3,
                        'max_val': 3}
        self.writer = None
        self.ao_task = None

        self.ao_counter = 0
        self.ai_counter = 0

        self.frames = []
        self.reading_image_callback = None
        # Could use a clock to drive both tasks, but not sure if helps at all?
        # sample_clk_task = nidaqmx.Task()
        # self.sample_clk_task = sample_clk_task
        # sample_clk_task.co_channels.add_co_pulse_chan_freq(f'{devname}/ctr0', freq=sample_rate)
        # sample_clk_task.timing.cfg_samp_clk_timing(sample_rate, sample_mode=)
        # # sample_clk_task.timing.cfg_implicit_timing(samps_per_chan=nsamples)
        # samp_clk_terminal = f'/{devname}/Ctr0InternalOutput'

        # # write_task.timing.cfg_samp_clk_timing(sample_rate, source=samp_clk_terminal, active_edge=nidaqmx.constants.Edge.RISING, samps_per_chan=nsamples)
        # write_task.timing.cfg_samp_clk_timing(sample_rate, source=samp_clk_terminal, active_edge=nidaqmx.constants.Edge.RISING,
        #                                       sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=bufsize)

    @property
    def fps(self):
        return self.sample_rate / (self.pixels_x * self.pixels_y * self.samples_per_pixel)

    @property
    def pixels_y(self):
        return round(self.pixels_x * self.y_amp / self.x_amp)

    @property
    def samples_per_refresh(self):
        return round(self.sample_rate / self.fps)

    @property
    def timebase(self):
        return np.arange(self.samples_per_refresh) / self.sample_rate

    def init_ai(self):
        self.ai_task = nidaqmx.Task()
        for ch in self.ai_channels:
            self.ai_task.ai_channels.add_ai_voltage_chan(self.devname + ch, **self.ai_args)
        self.read_buffer = np.zeros((len(self.ai_channels), self.samples_per_refresh), dtype=np.float64)
        self.ai_task.timing.cfg_samp_clk_timing(rate=self.sample_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
        # Configure ai to start only once ao is triggered for simultaneous generation and acquisition:
        self.ai_task.triggers.start_trigger.cfg_dig_edge_start_trig("ao/StartTrigger", trigger_edge=nidaqmx.constants.Edge.RISING)

        self.ai_task.in_stream.input_buf_size = self.samples_per_refresh * len(self.ai_channels) * self.buffer_oversize
        self.reader = stream_readers.AnalogMultiChannelReader(self.ai_task.in_stream)
        self.ai_task.register_every_n_samples_acquired_into_buffer_event(self.samples_per_refresh, self.reading_task_callback)

    def init_ao(self):
        ao_task = nidaqmx.Task()
        self.ao_task = ao_task
        for ch in self.ao_channels:
            ao_task.ao_channels.add_ao_voltage_chan(self.devname + ch, **self.ao_args)
        ao_task.timing.cfg_samp_clk_timing(rate=self.sample_rate, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS)
        # Set output buffer to correct size
        ao_task.out_stream.output_buf_size = self.samples_per_refresh * len(self.ao_channels) * self.buffer_oversize
        self.writer = stream_writers.AnalogMultiChannelWriter(ao_task.out_stream)
        # fill buffer for first time
        for _ in range(self.buffer_oversize):
            self.writer.write_many_sample(self.waveform())

        self.ao_task.register_every_n_samples_transferred_from_buffer_event(self.samples_per_refresh, self.writing_task_callback)

    def init_tasks(self):
        self.init_ai()
        self.init_ao()

    def start(self):
        if self.ai_task is None or self.ao_task is None:
            self.init_tasks()
        self.ai_task.start()
        self.ao_task.start()

    def stop(self):
        if self.ai_task is not None:
            self.ai_task.stop()
        if self.ao_task is not None:
            self.ao_task.stop()
        self.ai_counter = 0
        self.ao_counter = 0

    def close(self):
        if self.ai_task is not None:
            self.ai_task.close()
            self.ai_task = None
        if self.ao_task is not None:
            self.ao_task.close()
            self.ao_task = None

    # def __del__(self):
    #     self.close()

    def set_voltages(self, voltages):
        # Voltages - tuple, len channels
        assert len(voltages) == len(self.ao_channels)

        assert self.ao_task is None, "Can't set voltages when task is active, call .stop first"

        # make temp channel and writer
        with nidaqmx.Task() as temptask:
            for ch in self.ao_channels:
                temptask.ao_channels.add_ao_voltage_chan(self.devname + ch, **self.ao_args)

            temptask.write(np.asarray(voltages, dtype=np.float64), timeout=2.0, auto_start=True)
            temptask.wait_until_done()
            temptask.stop()

    def zero_output(self):
        self.set_voltages([0, ] * len(self.ao_channels))

    def park(self, parkXvolts=8, parkYvolts=8, amp_volts=0):
        self.set_voltages((parkXvolts, parkYvolts, amp_volts))

    def waveform(self):
        # Use a starting phase offset to ensure waveform generation is smooth, even if other waveform parameters change

        # X fast scanner
        # creates 0 to 1 saw wave
        xraw = ((np.arange(self.samples_per_refresh) + 1) % (self.samples_per_pixel * self.pixels_x)) / (self.samples_per_pixel * self.pixels_x)
        xscaled = (xraw - 0.5) * self.x_amp + self.x_offset

        xscaled = np.pad(np.cumsum(gaussian_filter1d(np.diff(xraw), sigma=10)), (1, 0))

        # Y slow scanner
        yscaled = np.linspace(self.y_offset - self.y_amp / 2, self.y_offset + self.y_amp / 2, self.samples_per_refresh)

        # laser amplitude control, turn off laser near flyback/edges
        # ampdata = ((unscaled_wave < .95) & (unscaled_wave > .05)).astype(int)

        # plt.figure()
        # plt.plot(xscaled)
        # plt.plot(yscaled)
        # plt.show()

        stacked_wave = np.vstack((xscaled, yscaled))
        stacked_wave = np.clip(stacked_wave, self.ao_args['min_val'], self.ao_args['max_val'])
        # print(stacked_wave.shape) # shape should be nchannels, nsamples
        return stacked_wave

    def writing_task_callback(self, task_idx, event_type, num_samples, callback_data):
        """This callback is called every time a defined amount of samples have been transferred from the device output
        buffer. This function is registered by register_every_n_samples_transferred_from_buffer_event and it must follow
        prototype defined in nidaqxm documentation.

        Args:
            task_idx (int): Task handle index value
            event_type (nidaqmx.constants.EveryNSamplesEventType): TRANSFERRED_FROM_BUFFER
            num_samples (int): Number of samples that was writen into the write buffer.
            callback_data (object): User data - I use this arg to pass signal generator object.
        """
        self.writer.write_many_sample(self.waveform(), timeout=5.0)
        self.ao_counter += 1

        # The callback function must return 0 to prevent raising TypeError exception.
        return 0

    def reading_task_callback(self, task_idx, event_type, num_samples, callback_data=None):
        """This callback is called every time a defined amount of samples have been acquired into the input buffer. This
        function is registered by register_every_n_samples_acquired_into_buffer_event and must follow prototype defined
        in nidaqxm documentation.

        Args:
            task_idx (int): Task handle index value
            event_type (nidaqmx.constants.EveryNSamplesEventType): ACQUIRED_INTO_BUFFER
            num_samples (int): Number of samples that were read into the read buffer.
            callback_data (object)[None]: User data can be additionally passed here, if needed.
        """

        self.reader.read_many_sample(self.read_buffer, num_samples, timeout=nidaqmx.constants.WAIT_INFINITELY)
        newframe = self.read_buffer.copy().astype(np.float32).reshape(self.pixels_y, self.pixels_x).T
        # TODO assuming one channel
        if self.reading_image_callback:
            self.reading_image_callback(newframe)
        self.frames.append(newframe)
        self.ai_counter += 1

        # The callback function must return 0 to prevent raising TypeError exception.
        return 0


if __name__ == '__main__':
    import time

    gen = WaveformGen(devname='Dev1')
    print(f"FPS: {gen.fps}")
    gen.start()
    time.sleep(4)
    gen.close()
    from skimage import io

    data = gen.read_buffer.copy()
    io.imsave('x.tiff', np.stack([f[0, ...].reshape((gen.pixels_y, gen.pixels_x)) for f in gen.frames]))
    io.imsave('y.tiff', np.stack([f[1, ...].reshape((gen.pixels_y, gen.pixels_x)) for f in gen.frames]))

    print(data.shape)

    plt.figure()
    plt.plot(data[0, :])
    plt.plot(data[1, :])
    plt.show()

    # gen.start()
    # gen.set_voltages((1, 2, 3))
    # gen.start()
    # gen.zero_output()
    # time.sleep(3)
    # gen.close()
