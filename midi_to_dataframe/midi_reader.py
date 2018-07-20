import logging
import midi
import pandas as pd
from collections import defaultdict
from collections import OrderedDict
from enum import Enum
from collections import namedtuple

# Named time signature tuple, i.e. 4/4, 5/4, etc.
TimeSignature = namedtuple('TimeSignature', 'numerator denominator')

# Constants
DEFAULT_MIDI_BPM = 120
DEFAULT_MIDI_PROGRAM_NUM = -1
DEFAULT_MIDI_TIME_SIGNATURE = TimeSignature(4, 4)
MIDI_DRUM_CHANNEL = 9
REST = "rest"
IDENTIFIER_NUMERATOR = "numerator"
IDENTIFIER_DENOMINATOR = "denominator"
IDENTIFIER_BPM = "bpm"
IDENTIFIER_RESOLUTION = "resolution"


class NoteLength(Enum):
    """
    Valid quantization values. Defined as ratios of quarter notes.
    """
    QUARTER = 1
    EIGHTH = 0.5
    SIXTEENTH = 0.25
    THIRTY_SECOND = 0.125


# Default quantization factors
DEFAULT_DURATION_QUANTIZATION = NoteLength.SIXTEENTH.value
DEFAULT_TIMING_QUANTIZATION = NoteLength.SIXTEENTH.value


class MidiReader(object):
    """
    Interface for reading data from MIDI files.
    """

    def __init__(self, note_mapper):
        """
        Creates a new MidiReader instance.
        :return: None.
        """
        self._logger = logging.getLogger(__name__)

        # Note mapping configuration to use
        self._note_mapper = note_mapper

        # Note duration and timing quantization settings
        self._duration_quantization_ratio = DEFAULT_DURATION_QUANTIZATION
        self._timing_quantization_ratio = DEFAULT_TIMING_QUANTIZATION

        # MIDI file resolution (ticks per quarter note)
        self._resolution = 120

        # Time signature changes, stored by timestamp
        self._time_signature_by_timestamp = OrderedDict()

        # Tempo/BPM changes, stored by timestamp
        self._bpm_by_timestamp = OrderedDict()

        # Text representation of extracted notes, stored by timestamp
        self._text_sequence = defaultdict(list)

        # Temporary data store used during MIDI file to dataframe conversion
        self._on_notes = {}

        # Properties to extract from MIDI files
        self._extract_timestamp = True
        self._extract_bpm = True
        self._extract_time_signature = True
        self._extract_measure = True
        self._extract_beat = True

    def set_extract_timestamp(self, value):
        self._extract_timestamp = value

    def set_extract_bpm(self, value):
        self._extract_bpm = value

    def set_extract_time_signature(self, value):
        self._extract_time_signature = value

    def set_extract_measure(self, value):
        self._extract_measure = value

    def set_extract_beat(self, value):
        self._extract_beat = value

    def convert_to_dataframe(self, path):
        """
        Loads a MIDI file from disk and creates a Pandas Data Frame representing its MIDI events.
        :param path: the path to the MIDI file to load.
        :return: the Data Frame.
        """
        try:
            pattern = midi.read_midifile(path)
        except (TypeError, RuntimeWarning):
            self._logger.error("Could not load MIDI file: " + path)
            self._reset_intermediary_variables()
            return pd.DataFrame()

        pattern.make_ticks_abs()

        # pattern.resolution specifies the number of MIDI ticks used per quarter note in the pattern
        self._resolution = pattern.resolution

        # Convert the configured quantization values (specified in quarter notes) to MIDI ticks
        timing_quantization_ticks = int(pattern.resolution * self._timing_quantization_ratio)

        # Extract a textual representations of the MIDI pattern.
        self._extract_text_sequence(pattern)

        # Create (timestamp -> notes) mapping from the text sequence
        timestamp_sequence = self._create_timestamp_sequence(self._text_sequence, timing_quantization_ticks)

        # Check number of timestamp entries
        (max_timestamp, _) = max(self._text_sequence.items())
        if max_timestamp > 10000000:  # More than this becomes painfully slow...
            self._logger.error("Unable to process MIDI file (too many timestamps): " + path)
            self._reset_intermediary_variables()
            return pd.DataFrame()

        # Fill in blank beats, according to configured timing quantization rate
        for i in range(0, (max_timestamp + timing_quantization_ticks), timing_quantization_ticks):
            if i not in timestamp_sequence:
                timestamp_sequence[i] = REST

        data_rows = []

        measure = 1
        current_beat = 1
        time_sig = None
        for (index, (timestamp, notes)) in enumerate(sorted(timestamp_sequence.items())):

            row = {'notes': notes}

            # Extract current time index
            if self._extract_timestamp:
                row['timestamp'] = timestamp

            # Extract BPM at time index
            if self._extract_bpm:
                row['bpm'] = self._get_value_at_timestamp(self._bpm_by_timestamp, timestamp)

            # Extract time signature at time index
            prev_time_sig = time_sig
            time_sig = self._get_value_at_timestamp(self._time_signature_by_timestamp, timestamp)
            if self._extract_time_signature:
                row['time_signature'] = str(time_sig.numerator) + "/" + str(time_sig.denominator)

            # FIXME measure counts are wrong if quantization rate < time signature denominator
            # TODO refactor
            modifier = 1
            if self._timing_quantization_ratio == NoteLength.THIRTY_SECOND.value:
                modifier = 32 / time_sig.denominator
            elif self._timing_quantization_ratio == NoteLength.SIXTEENTH.value:
                modifier = 16 / time_sig.denominator
            elif self._timing_quantization_ratio == NoteLength.EIGHTH.value:
                modifier = 8 / time_sig.denominator
            elif self._timing_quantization_ratio == NoteLength.QUARTER.value:
                modifier = 4 / time_sig.denominator
            total_beat_units = (index / modifier)

            if self._timing_quantization_ratio == NoteLength.QUARTER.value:
                total_beat_units *= 2

            # Count number of beats so far this measure
            if total_beat_units > 0 and total_beat_units.is_integer():
                current_beat += 1

            # Count number of measures, reset current beat when measure increases
            if current_beat > time_sig.numerator or (prev_time_sig is not None and prev_time_sig != time_sig):
                measure += 1
                current_beat = 1

            beat = current_beat + total_beat_units % 1

            # Set current measure
            if self._extract_measure:
                row['measure'] = measure

            # Set current beat
            if self._extract_beat:
                row['beat'] = beat

            data_rows.append(row)

        # Since extraction is complete, reset all internal variables
        self._reset_intermediary_variables()

        # Create Data Frame from rows, stored as dictionaries
        dataframe = pd.DataFrame.from_dict(data_rows, orient='columns')

        # Put columns into correct order
        dataframe = self._reorder_cols(dataframe)

        return dataframe

    def _extract_text_sequence(self, pattern):
        """
        Processes a MIDI pattern by extracting a textual representation of all the notes played. The extracted text
        sequence is stored in self.text_sequence.
        :param pattern: the MIDI pattern to process.
        :return: None.
        """

        # Process each track of the input file in sequence
        for track in pattern:

            # Reset current program for each track
            # The program is a number that defines the instrument playing on the track
            current_program = None

            # Process all MIDI events in the track and store textual representation in self.text_sequence
            for event in track:
                # Updates current_program, since this may have been changed by the event
                current_program = self._process_midi_event(event, current_program)

        # In case BPM and Tempo were not set explicitly, assume MIDI defaults:
        if len(self._time_signature_by_timestamp) == 0:
            self._time_signature_by_timestamp[0] = DEFAULT_MIDI_TIME_SIGNATURE
        if len(self._bpm_by_timestamp) == 0:
            self._bpm_by_timestamp[0] = DEFAULT_MIDI_BPM

    @staticmethod
    def _create_timestamp_sequence(text_sequence, timing_quantization_ticks):
        """
        Create a single (timestamp, notes) mapping out of extracted note information.
        :param text_sequence: the extracted notes.
        :param timing_quantization_ticks: the quantization factor to use, in MIDI ticks.
        :return: a single (timestamp, notes) mapping of all extracted notes.
        """
        timestamp_sequence = {}
        for (timestamp, notes) in sorted(text_sequence.items()):

            if len(notes) > 0:

                # TODO why round down?
                timestamp = MidiReader._round_down(timestamp, timing_quantization_ticks)

                # Store notes as comma-separated string
                note_string = ','.join(list(notes))

                if timestamp in timestamp_sequence:
                    # If an entry already exists for the timestamp, append the notes to it
                    timestamp_sequence[timestamp] += ',' + note_string
                else:
                    # ...otherwise, create a new entry
                    timestamp_sequence[timestamp] = note_string

        return timestamp_sequence

    def _process_midi_event(self, event, program):
        """
        Processes a MIDI event played by a given MIDI program.
        :param event: the MIDI event to process.
        :param program: the current program of the MIDI track the event occurred on.
        :return: the updated program of the MIDI track (since this may have been updated by the MIDI event).
        """

        # Set program for drums, since this is set by channel and not explicitly
        if (type(event) == midi.NoteOnEvent or type(event) == midi.NoteOffEvent) and event.channel == MIDI_DRUM_CHANNEL:
            program = DEFAULT_MIDI_PROGRAM_NUM
        elif (type(event) == midi.NoteOnEvent or type(event) == midi.NoteOffEvent) and program is None:
            # If program was never set, default to 1 (Piano)
            program = 1

        # True Note On events have positive velocity
        if type(event) == midi.NoteOnEvent and event.velocity > 0:
            self._on_notes[event.pitch] = (event.tick, event)
        # Some sequences pass Note Off events encoded as a Note On event with 0 velocity
        elif type(event) == midi.NoteOffEvent or type(event) == midi.NoteOnEvent and event.velocity == 0:
            self._process_note_off(event.pitch, program, event.tick)
        elif type(event) == midi.TimeSignatureEvent:
            self._time_signature_by_timestamp[event.tick] = TimeSignature(event.get_numerator(),
                                                                          event.get_denominator())
        elif type(event) == midi.SetTempoEvent:
            self._bpm_by_timestamp[event.tick] = event.get_bpm()
        elif type(event) == midi.ProgramChangeEvent:
            program = event.value
        else:
            # TODO: not currently handled: pitch changes, control changes, ...
            pass

        return program

    def _process_note_off(self, note, program_num, current_tick):
        """
        Processes a note off message by adding a textual representation of the note to this instance's text sequence.
        :param note: the MIDI note being turned off.
        :param program_num: the program the note was played with.
        :param current_tick: the absolute MIDI tick timestamp when the note off message was encountered.
        :return: None.
        """

        # Check that note was previously turned on
        if note in self._on_notes:

            # Retrieve start time and original MIDI message for note
            (start_tick, prev_message) = self._on_notes[note]
            duration = current_tick - start_tick

            # Ensure note was actually played
            if duration > 0:

                # Convert duration from ticks to quarter notes
                duration = duration / self._resolution

                # Round duration to nearest step defined for instrument
                instrument = self._note_mapper.get_program_name(program_num)
                duration = self._note_mapper.round_duration(instrument, duration)

                # Round to 2 decimal places
                duration = self._round_to_sixteenth_note(duration)

                # Convert MIDI note name to name of instrument or octave/pitch name (depending on program)
                note_symbol = self._note_mapper.get_note_name(note, program_num)
                if note_symbol is not None:
                    # Concatenate instrument, note name and duration to create textual representation
                    # TODO replace underscore with constant/variable from note_mapping
                    # TODO allow customization of extracted note properties
                    representation = "{}_{}_{}".format(instrument, note_symbol, duration)

                    # Add note to the textual sequence representation
                    self._text_sequence[start_tick].append(representation)

            # Remove from on notes
            del self._on_notes[note]

        else:
            pass

    @staticmethod
    def _quantize(x, base):
        """
        Rounds a given number to a given fixed step size.
        :param x: the number to round.
        :param base: the allowed step size.
        :return: the quantized value.
        """
        if base > 0:
            rounded = int(base * round(float(x) / base))
            return rounded
        else:
            return base

    @staticmethod
    def _round_to_sixteenth_note(x):
        prec = 3
        base = 0.125
        return round(base * round(float(x) / base), prec)

    @staticmethod
    def _round_down(num, divisor):
        """
        Rounds a given number down to the nearest multiple of the divisor.
        :param num: the number to round down.
        :param divisor: the multiple to round down to.
        :return: the number, rounded down to the nearest multiple of the divisor given.
        """
        if divisor == 0:
            return 0
        return num - (num % divisor)

    @staticmethod
    def _get_value_at_timestamp(values, timestamp):
        """
        Searches an ordered dictionary of (timestamp, value) pairs for the value with the greatest timestamp lower than
        or equal to a given threshold timestamp.
        :param values: the ordered dictionary to search through.
        :param timestamp: the cutoff timestamp that the value should occur at or before.
        :return: the value found.
        """

        # Default to first element
        # TODO check if 'values' is empty
        keys = list(values.keys())
        value_at_timestamp = values[keys[0]]

        for (index, value) in values.items():
            if index <= timestamp:
                # Store value of highest timestamp encountered so far
                value_at_timestamp = value
            else:
                # Since values are sorted by timestamp, end the search early
                return value_at_timestamp

        return value_at_timestamp

    def _reorder_cols(self, dataframe):
        """
        Puts all extracted columns into the correct, expected order.
        :param dataframe: the dataframe whose columns will be reordered.
        :return: dataframe with reordered columns.
        """
        correct_col_order = []
        if self._extract_timestamp:
            correct_col_order.append('timestamp')
        if self._extract_bpm:
            correct_col_order.append('bpm')
        if self._extract_time_signature:
            correct_col_order.append('time_signature')
        if self._extract_measure:
            correct_col_order.append('measure')
        if self._extract_beat:
            correct_col_order.append('beat')
        correct_col_order.append('notes')
        return dataframe[correct_col_order]

    def _reset_intermediary_variables(self):
        """
        Clears all stateful variables used during MIDI-to-text conversion.
        :return: None.
        """
        self._time_signature_by_timestamp = OrderedDict()
        self._bpm_by_timestamp = OrderedDict()
        self._text_sequence = defaultdict(list)
        self._on_notes = {}
