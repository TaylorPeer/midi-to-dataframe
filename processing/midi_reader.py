import midi
import pandas as pd
from collections import defaultdict
from collections import OrderedDict
from enum import Enum
from collections import namedtuple

# Constants
DEFAULT_MIDI_PROGRAM_NUM = -1
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

# Named time signature tuple, i.e. 4/4, 5/4, etc.
TimeSignature = namedtuple('TimeSignature', 'numerator denominator')


class MidiReader(object):
    """
    Interface for reading data from MIDI files.
    """

    def __init__(self, note_mapper):
        """
        Creates a new MidiReader instance.
        :return: None.
        """

        # Note mapping configuration to use
        self.note_mapper = note_mapper

        # Note duration and timing quantization settings
        self.duration_quantization_ratio = DEFAULT_DURATION_QUANTIZATION
        self.timing_quantization_ratio = DEFAULT_TIMING_QUANTIZATION

        # MIDI file resolution (ticks per quarter note)
        self.resolution = 120

        # Time signature changes, stored by timestamp
        self.time_signatures = OrderedDict()

        # Tempo/BPM changes, stored by timestamp
        self.bpms = OrderedDict()

        # Text representation of extracted notes, stored by timestamp
        self.text_sequence = defaultdict(list)

        # Temporary data store used during MIDI file processing
        self.on_notes = {}

    def set_duration_quantization(self, duration_quantization):
        """
        Sets the note duration quantization interval (in quarter notes).
        :param duration_quantization: the quantization value to use.
        :return: None.
        """
        self.duration_quantization_ratio = duration_quantization.value

    def set_timing_quantization(self, timing_quantization):
        """
        Sets the note timing quantization interval (in quarter notes).
        :param timing_quantization: the quantization value to use.
        :return: None.
        """
        self.timing_quantization_ratio = timing_quantization.value

    @staticmethod
    def quantize(x, base):
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
    def round_down(num, divisor):
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
    def get_value_at_timestamp(values, timestamp):
        """
        Searches an ordered dictionary of (timestamp, value) pairs for the value with the greatest timestamp lower than
        or equal to a given threshold timestamp.
        :param values: the ordered dictionary to search through.
        :param timestamp: the cutoff timestamp that the value should occur at or before.
        :return: the value found.
        """

        # Default to first element
        # TODO check if values is empty
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

    def extract_text_sequence(self, pattern, duration_quantization_ticks):
        """
        Processes a MIDI pattern by extracting a textual representation of all the notes played. The extracted text
        sequence is stored in self.text_sequence.
        :param pattern: the MIDI pattern to process.
        :param duration_quantization_ticks: the factor to quantize MIDI note durations by, in MIDI ticks.
        :return: None.
        """

        # Process each track of the input file in sequence
        for track in pattern:

            # Reset current program for each track
            # The program is a number that defines the instrument playing on the track
            current_program = DEFAULT_MIDI_PROGRAM_NUM

            # Process all MIDI events in the track and store textual representation in self.text_sequence
            for event in track:
                # Updates current_program, since this may have been changed by the event
                current_program = self.process_midi_event(event, current_program, duration_quantization_ticks)

    @staticmethod
    def create_timestamp_sequence(text_sequence, timing_quantization_ticks):
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
                timestamp = MidiReader.round_down(timestamp, timing_quantization_ticks)

                # Store notes as comma-separated string
                note_string = ','.join(list(notes))

                if timestamp in timestamp_sequence:
                    # If an entry already exists for the timestamp, append the notes to it
                    timestamp_sequence[timestamp] += ',' + note_string
                else:
                    # ...otherwise, create a new entry
                    timestamp_sequence[timestamp] = note_string

        return timestamp_sequence

    def convert_to_dataframe(self, path):
        """
        Loads a MIDI file from disk and creates a timestamped text sequence representing its MIDI events.
        :param path: the path to the MIDI file to load.
        :return: the timestamped text sequence and associated metadata fields created for the MIDI file.
        """
        try:
            pattern = midi.read_midifile(path)
        except TypeError:
            print("Could not load MIDI file: " + path)  # TODO log
            return {}, {}

        pattern.make_ticks_abs()

        # pattern.resolution specifies the number of MIDI ticks used per quarter note in the pattern
        self.resolution = pattern.resolution

        # Convert the configured quantization values (specified in quarter notes) to MIDI ticks
        duration_quantization_ticks = int(pattern.resolution * self.duration_quantization_ratio)
        timing_quantization_ticks = int(pattern.resolution * self.timing_quantization_ratio)

        # Extract a textual representations of the MIDI pattern.
        self.extract_text_sequence(pattern, duration_quantization_ticks)

        # Create (timestamp -> notes) mapping from the text sequence
        timestamp_sequence = MidiReader.create_timestamp_sequence(self.text_sequence, timing_quantization_ticks)

        # Fill in blank beats, according to configured timing quantization rate
        (max_timestamps, _) = max(self.text_sequence.items())
        for i in range(0, (max_timestamps + timing_quantization_ticks), timing_quantization_ticks):
            if i not in timestamp_sequence:
                timestamp_sequence[i] = REST

        # TODO make extracted values configurable (bpm, time signature, etc.)
        data_rows = []
        measure = 1
        current_beat = 1
        prev_time_sig = None
        time_sig = None
        for (index, (timestamp, notes)) in enumerate(sorted(timestamp_sequence.items())):

            row = {'timestamp': timestamp, 'notes': notes}

            # Extract BPM at time index
            row['bpm'] = MidiReader.get_value_at_timestamp(self.bpms, timestamp)

            # Extract time signature at time index
            prev_time_sig = time_sig
            time_sig = MidiReader.get_value_at_timestamp(self.time_signatures, timestamp)
            row['time_signature'] = str(time_sig.numerator) + "/" + str(time_sig.denominator)

            # TODO refactor
            modifier = 1
            if self.timing_quantization_ratio == NoteLength.THIRTY_SECOND.value:
                modifier = 32 / time_sig.denominator
            elif self.timing_quantization_ratio == NoteLength.SIXTEENTH.value:
                modifier = 16 / time_sig.denominator
            elif self.timing_quantization_ratio == NoteLength.EIGHTH.value:
                modifier = 8 / time_sig.denominator
            elif self.timing_quantization_ratio == NoteLength.QUARTER.value:
                modifier = 4 / time_sig.denominator
            total_beat_units = (index / modifier)

            # Count number of beats so far this measure
            if total_beat_units > 0 and total_beat_units.is_integer():
                current_beat += 1

            # Count number of measures, reset current beat when measure increases
            if current_beat > time_sig.numerator or (prev_time_sig is not None and prev_time_sig != time_sig):
                measure += 1
                current_beat = 1

            beat = current_beat + total_beat_units % 1

            # Set current measure and beat
            row["measure"] = measure
            row["beat"] = beat

            data_rows.append(row)

        # Since extraction is complete, reset all internal variables
        self.reset_intermediary_variables()

        # Create Data Frame from rows, stored as dictionaries
        dataframe = pd.DataFrame.from_dict(data_rows, orient='columns')

        # Re-order columns
        dataframe = dataframe[['timestamp', 'bpm', 'time_signature', 'measure', 'beat', 'notes']]

        return dataframe

    def reset_intermediary_variables(self):
        """
        Clears all stateful variables used during MIDI-to-text conversion.
        :return: None.
        """
        self.time_signatures = OrderedDict()
        self.bpms = OrderedDict()
        self.text_sequence = defaultdict(list)
        self.on_notes = {}

    def process_midi_event(self, event, program, duration_quantization_ticks):
        """
        Processes a MIDI event played by a given MIDI program.
        :param event: the MIDI event to process.
        :param program: the current program of the MIDI track the event occurred on.
        :param duration_quantization_ticks: the quantization rate to use for standardizing note duration (in MIDI ticks).
        :return: the updated program of the MIDI track (since this may have been updated by the MIDI event).
        """

        # Set program to default for drums
        if type(event) == midi.NoteOnEvent or type(event) == midi.NoteOffEvent and event.channel == MIDI_DRUM_CHANNEL:
            program = DEFAULT_MIDI_PROGRAM_NUM

        # True Note On events have positive velocity
        if type(event) == midi.NoteOnEvent and event.velocity > 0:
            self.on_notes[event.pitch] = (event.tick, event)
        # Some sequences pass Note Off events encoded as a Note On event with 0 velocity
        elif type(event) == midi.NoteOffEvent or type(event) == midi.NoteOnEvent and event.velocity == 0:
            self.process_note_off(event.pitch, program, event.tick, duration_quantization_ticks)
        elif type(event) == midi.TimeSignatureEvent:
            self.time_signatures[event.tick] = TimeSignature(event.get_numerator(), event.get_denominator())
        elif type(event) == midi.SetTempoEvent:
            self.bpms[event.tick] = event.get_bpm()
        elif type(event) == midi.ProgramChangeEvent:
            program = event.value
        else:
            # TODO: not currently handled: pitch changes, control changes, ...
            pass

        return program

    def process_note_off(self, note, program, current_tick, duration_quantization):
        """
        Processes a note off message by adding a textual representation of the note to this instance's text sequence.
        :param note: the MIDI note being turned off.
        :param program: the program the note was played with.
        :param current_tick: the absolute MIDI tick timestamp when the note off message was encountered.
        :param duration_quantization: the quantization factor to use for note duration values.
        :return: None.
        """

        # Check that note was previously turned on
        if note in self.on_notes:

            # Retrieve start time and original MIDI message for note
            (start_tick, prev_message) = self.on_notes[note]
            duration = current_tick - start_tick

            # Ensure note was actually played
            if duration > 0:

                # Check the MIDI program to determine the instrument
                if program < 0:
                    duration = duration_quantization
                else:
                    duration = MidiReader.quantize(duration, duration_quantization)

                # Convert duration from ticks to quarter notes
                duration = duration / self.resolution

                # Convert MIDI note name to name of instrument or octave/pitch name (depending on program)
                note_symbol = self.note_mapper.get_note(note, program)
                if note_symbol is not None:
                    # Concatenate instrument, note name and duration to create textual representation
                    # TODO replace underscore with constant/variable from note_mapping
                    # TODO allow customization of extracted note properties
                    representation = self.note_mapper.get_instrument(program) + "_" + note_symbol + "_" + str(
                        duration)

                    # Add note to the textual sequence representation
                    self.text_sequence[start_tick].append(representation)

            # Remove from on notes
            del self.on_notes[note]

        else:
            pass
