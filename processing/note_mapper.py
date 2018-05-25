import json

# Letter notation for music notes
# TODO: make this configurable, for varying notation systems
NOTE_NAMES = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]

# Maximum index of MIDI notes
MAX_MIDI_NOTE = 127

MIDI_TO_TEXT = "midi-to-text"
PERCUSSION = "percussion"


class NoteMapper(object):
    """
    Mapper object to convert between MIDI notes and their textual representations.
    """

    def __init__(self, path_to_config):
        """
        Creates a new NoteMapper instance.
        :return: None.
        """

        # Load MIDI mapping configuration
        with open(path_to_config) as json_data:
            # TODO: validate JSON
            self.mappings = json.load(json_data)

        # Initialize note names and number
        index = 0
        self.notes = {}
        for octave in range(0, 11):
            for n in NOTE_NAMES:
                if index <= MAX_MIDI_NOTE:
                    symbol = n + str(octave)
                    self.notes[index] = symbol
                    index += 1

    def get_note(self, note, program):
        """
        Returns a string representation of a note and the program it is played on.
        :param note: the note.
        :param program: the program the note is played on.
        :return: the note's string representation (or None, if it could not be determined).
        """
        if program >= 0 and note in self.notes:
            return self.notes[note]
        elif str(note) in self.mappings[MIDI_TO_TEXT][PERCUSSION]:
            return self.mappings[MIDI_TO_TEXT][PERCUSSION][str(note)]
        else:
            # TODO collect number of errors, count by note / program, log only when called
            if program >= 0:
                # TODO temporarily disabled:
                # print("Note not found in configured mapping: " + str(note) + " on channel: " + str(program))
                pass
            else:
                # TODO temporarily disabled:
                # print("Note not found in configured mapping " + str(note) + " on drum channel.")
                pass
        return None

    def get_instrument(self, program):
        """
        Returns a string representation for a given MIDI program (instrument).
        :param program: the program.
        :return: the program's string representation.
        """
        if program >= 0:
            return self.mappings[MIDI_TO_TEXT][str(program)]
        else:
            return PERCUSSION
