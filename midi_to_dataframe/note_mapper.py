import logging
import json

# Letter notation for music notes
# TODO: make this configurable, for varying notation systems
NOTE_NAMES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]

# MIDI constants
MAX_MIDI_NOTE_NUM = 127
MAX_OCTAVE_INDEX = 11

# Internal string constants
MIDI_TO_TEXT = "midi-to-text"
TEXT_TO_MIDI = "text-to-midi"
PERCUSSION = "percussion"
DURATIONS = "durations"


class NoteMapper(object):
    """
    Mapper object to convert between symbolic (MIDI) notes and their textual representations.
    """

    def __init__(self, path_to_config):
        """
        Creates a new NoteMapper instance.
        :return: None.
        """
        self._logger = logging.getLogger(__name__)

        # Load MIDI mapping configuration
        with open(path_to_config) as json_data:
            # TODO: validate JSON
            self.mappings = json.load(json_data)

        # Allowed durations by instrument/program
        self.duration_values = self.mappings[DURATIONS]

        # Initialize note names and numbers
        index = 0
        self._notes = {}
        for octave in range(0, MAX_OCTAVE_INDEX):
            for n in NOTE_NAMES:
                if index <= MAX_MIDI_NOTE_NUM:
                    symbol = n + str(octave)
                    self._notes[index] = symbol
                    index += 1

        # Log note lookup failures for later inspection
        self._note_lookup_failures = {}

    def round_duration(self, program, duration):
        """
        Rounds the duration of a note played on a given program to the nearest configured step size.
        :param program: the program name the note was played on.
        :param duration: the raw duration value to round, in quarter notes.
        :return: the rounded duration value.
        """
        if program in self.duration_values:
            allowed_values = self.duration_values[program]
            rounded = min(allowed_values, key=lambda x: abs(x - duration))
            return rounded
        else:
            self._logger.error("No duration mapping defined for: {}".format(program))
        return 0

    def get_program_name(self, program_number):
        """
        Returns a string representation for a given MIDI program number.
        :param program_number: the MIDI program number.
        :return: the program's string representation.
        """
        if program_number >= 0:
            return self.mappings[MIDI_TO_TEXT][str(program_number)]
        else:
            return PERCUSSION

    def get_program_number(self, program_name):
        """
        Returns a MIDI program number for a given program name.
        :param program_name: the name of the MIDI program number.
        :return: the program number.
        """
        if program_name != PERCUSSION:
            return self.mappings[TEXT_TO_MIDI][str(program_name)]
        else:
            return -1

    def get_note_name(self, note_number, program_number):
        """
        Returns a string representation of a note and the program it is played on.
        :param note_number: the MIDI note (pitch) number.
        :param program_number: the program the note is played on.
        :return: the note's string representation (or None, if it could not be determined).
        """
        if program_number >= 0 and note_number in self._notes:
            return self._notes[note_number]
        elif str(note_number) in self.mappings[MIDI_TO_TEXT][PERCUSSION]:
            return self.mappings[MIDI_TO_TEXT][PERCUSSION][str(note_number)]
        else:
            self._log_note_lookup_failure(program_number, note_number)
        return None

    def get_note_number(self, note_name):
        """
        Returns the MIDI note number for the given symbolic note name.
        :param note_name: the note name to look up.
        :return: the corresponding MIDI note number.
        """
        for note_number, symbolic_name in self._notes.items():
            if symbolic_name == note_name:
                return note_number
        for drum_number, symbolic_name in self.mappings[MIDI_TO_TEXT][PERCUSSION].items():
            if symbolic_name == note_name:
                return int(drum_number)
        return -1

    def get_note_lookup_failures(self):
        """
        Returns the collection of logged note lookup failures.
        :return: dictionary containing note lookup failure counts.
        """
        return self._note_lookup_failures

    def _log_note_lookup_failure(self, program_number, note_number):
        """
        Logs that a note name lookup for a given program and note number combination.
        :param program_number: the MIDI program number of the failed lookup.
        :param note_number: the MIDI note number of the failed lookup.
        :return: None.
        """

        # Get previous failures for this program number
        if program_number in self._note_lookup_failures:
            failures_for_prog = self._note_lookup_failures[program_number]
        else:
            failures_for_prog = {}

        # Get previous failures for this note number
        if note_number in failures_for_prog:
            failures_for_note = failures_for_prog[note_number]
        else:
            failures_for_note = 0

        # Log failure
        failures_for_note += 1
        failures_for_prog[note_number] = failures_for_note
        self._note_lookup_failures[program_number] = failures_for_prog
