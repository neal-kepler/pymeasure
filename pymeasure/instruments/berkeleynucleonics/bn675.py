#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2020 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_range, strict_discrete_set
from time import time
from pyvisa.errors import VisaIOError

class Channel(object):

    polarity = Instrument.control(
        "POLarity?", "POLarity %s",
        """ A string property controlling the output polarity. 'NORM' or 'INV'.""",
        validator=strict_range,
        values=['NORM', 'INV'],
    )

    output = Instrument.control(
        "STAT?", "STAT %d",
        """ A boolean property that turns on (True) or off (False) the output
        of the function generator. Can be set. """,
        validator=strict_discrete_set,
        map_values=True,
        values={True: 1, False: 0},
    )

    offset = Instrument.control(
        "BLOF?","BLOF %g",
        """ A floating point property that controls the amplitude
        offset. It is always in Volt. This property can be set.""",
        validator=strict_range,
        values=[-2, 2]
    )



    def __init__(self, instrument, number):
        self.instrument = instrument
        self.number = number
        self._elem = None
        self._elemprefix = None

    def values(self, command, **kwargs):
        """ Reads a set of values from the instrument through the adapter,
        passing on any key-word arguments.
        """
        return self.instrument.values("source%d:%s" % (
                                      self.number, command), **kwargs)
    def ask(self, command):
        self.instrument.query("output%d:%s" % (self.number, command))

    def write(self, command):
        self.instrument.write("output%d:%s" % (self.number, command))

    def read(self):
        self.instrument.read()

    def enable(self):
        self.instrument.write("output%d:state on" % self.number)

    def disable(self):
        self.instrument.write("output%d:state off" % self.number)

    @property
    def active_sequence_elem(self):
        return self._elem

    @active_sequence_elem.setter
    def active_sequence_elem(self,elem):
        self._elem = elem
        self._elemprefix = f"SEQ:ELEM{elem}:"

    @property
    def waveform(self):
        return self.instrument.query(self._elemprefix+f"WAV{self.number}?")

    @waveform.setter
    def waveform(self, wfname):
        self.instrument.query(self._elemprefix + f"WAV{self.number} \"{wfname}\"")

    @property
    def amplitude(self):
        return self.instrument.query(self._elemprefix + f"AMP{self.number}?")

    @amplitude.setter
    def amplitude(self, amp):
        self.instrument.query(self._elemprefix + f"AMP{self.number} {amp}")

    @property
    def offset(self):
        return self.instrument.query(self._elemprefix + f"OFF{self.number}?")

    @offset.setter
    def offset(self, offset):
        self.instrument.query(self._elemprefix + f"OFF{self.number} {offset}")


class BN675_AWG(Instrument):
    """Represents the Berkeley nucleonics arbitrary waveform generator. WIP
    This AWG can switch between an AWG and an AFG. This driver is for the AWG. There
    is a SCPI command to switch between them but it is not implemented here.
    Each channel has its own sequencer, but to maintain synchronicity, the length of each
    channels' sequence must be the same. Because this is 2021, the AWG helpfully maintains
    a set of strategies to fix length mismatches from which you may choose. As such, the way
    AWG's are specified is "SEQ:ELEM[n]:WAV[m] wfname" where n is the n'th part in the sequence table and
    m is the channel to put the waveform with wfname.

    """

    burst_n_cyces = Instrument.control(
        "AWGC:BURST?", "AWGC:BURST %d",
        """ Integer parameter setting the number of cycles to burst in burst mode""",
    )

    num_channels = Instrument.measurement(
        "AWGC:CONF:CNUM?", """Returns the number of analog channels on the instrument"""
    )

    run_mode = Instrument.control(
        "AWGControl:RMODe?", "AWGControl:RMODe %s",
        """ A string parameter controlling the AWG run mode. Can be:
        CONT: output continously outputs WF
        BURST: burst n after trigger
        TCON: go into continous mode after trigger
        STEP: each trigger event causes the next wf in sequencer to fire
        ADVA: allows conditional hops around sequencer table""",
        validator=strict_discrete_set,
        values=['CONT', 'BURST', 'TCON', 'STEP', 'ADVA'],
    )

    run_state = Instrument.measurement(
        "AWGC:RSTAT", """Queries the run state: 0 is stopped
        1 is waiting for trigger, 2 is running"""
    )

    sampling_frequency = Instrument.control(
        "AWGC:SRAT?", "AWGC:SRAT %e",
        """ A floating point property that controls AWG sampling frequency.
        This property can be set.""",
        validator=strict_range,
        values=[10e6, 1.2e9]
    )

    trigger_source = Instrument.control(
        "TRIGger:SEQUENCE:SOURce?", "TRIGger:SEQUENCE:SOURce %s",
        """ A string parameter to set the whether the trigger is TIMer, EXTernal (BNC),
         or MANual (front panel or software) """,
        validator=strict_discrete_set,
        values=['TIM', 'EXT', 'MAN']
    )


    trigger_slope = Instrument.control(
        "TRIGger:SEQUENCE:SLOPe?", "TRIGger:SEQUENCE:SLOPe %s",
        """ A string parameter to set the whether the trigger edge is POSitive or NEGative, or BOTH""",
        validator=strict_discrete_set,
        values={'POS': 'POS', 'NEG': 'NEG', 'BOTH': 'BOTH'},
        map_values=True
    )

    trigger_level = Instrument.control(
        "TRIGger:SEQUENCE:LEVel?", "TRIGger:SEQUENCE:LEVel %g",
        """ A float parameter that sets the trigger input level threshold. Unclear what the range is,
        0.2 V - 1.4 V is a valid range""",
    )

    trigger_impedance = Instrument.control(
        "TRIGger:SEQUENCE:IMPedance?", "TRIGger:SEQUENCE:IMPedance %s",
        """ An integer parameter to set the trigger input impedance to either 50 or 1000 Ohms""",
        validator=strict_discrete_set,
        values={50: '50 Ohm',1000:'1 KOhm'},
        map_values=True
    )

    sequence_len = Instrument.control(
        "SEQ:LENG?", "SEQ:LENG %d",
        """ Integer atrribute to control the length of the sequence table for all channels""",
        validator=strict_discrete_set,
        values={50: '50 Ohm', 1000: '1 KOhm'},
        map_values=True
    )




    def __init__(self, adapter, **kwargs):
        super(BN675_AWG, self).__init__(
            adapter,
            "BN675 arbitrary waveform generator",
            **kwargs
        )
        num_chan = int(self.num_channels)
        for i in range(num_chan):
            setattr(self,f'ch{i+1}', Channel(self, i+1))

    def beep(self):
        self.write("system:beep")

    def trigger(self):
        """ Send a trigger signal to the function generator. """
        self.write("*TRG")

    def wait_for_trigger(self, timeout=3600, should_stop=lambda: False):
        """ Wait until the triggering has finished or timeout is reached.

        :param timeout: The maximum time the waiting is allowed to take. If
                        timeout is exceeded, a TimeoutError is raised. If
                        timeout is set to zero, no timeout will be used.
        :param should_stop: Optional function (returning a bool) to allow the
                            waiting to be stopped before its end.

        """

        t0 = time()
        while True:
            try:
                ready = self.run_state
            except VisaIOError:
                ready = -1

            if ready != 0:
                return

            if timeout != 0 and time() - t0 > timeout:
                raise TimeoutError(
                    "Timeout expired while waiting for the WAS8104A" +
                    " to finish the triggering."
                )

            if should_stop:
                return

    def opc(self):
        return int(self.query("*OPC?"))


    def start_awg(self):
        self.write('AWGC:RUN')

    def stop_awg(self):
        self.write('AWGC:STOP')

    def load_waveform_from_file(self, name, pathtofile):
        #todo implement analog, digital specification
        """
        Loads a waveform at pathtofile to the waveform list with name. The default behavior assumes analog data
        """
        self.write("wlist:waveform:import \"%s\",\"%s\"" % (name,pathtofile))


    def delete_waveform(self, name):
        """
        Defines an empty waveform of name, of integer length size of datatype ('INT' or 'REAL'
        """
        self.write("wlist:waveform:delete \"%s\"" % name)

