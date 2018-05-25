import unittest

from processing.note_mapper import NoteMapper
from processing.midi_reader import MidiReader, NoteLength

MIDI_FILE_1 = "resources/processing/midi/080 Downtempo 08.mid"
MIDI_FILE_2 = "resources/processing/midi/090 New York.mid"
MIDI_FILE_3 = "resources/processing/midi/135 Garage 02.mid"
MIDI_FILE_4 = "resources/processing/midi/170 Jungle 09.mid"
MIDI_FILE_5 = "resources/processing/midi/freestyler-clip.mid"
MIDI_FILE_6 = "resources/processing/midi/Bomfunk_MCs_-_Freestyler.mid"
MIDI_FILE_7 = "resources/processing/midi/Tool_-_The_grudge.mid"


class MidiReaderTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MidiReaderTests, self).__init__(*args, **kwargs)

        # Prepare test objects
        note_mapping_config_path = "resources/processing/config/map-to-group.json"
        note_mapper = NoteMapper(note_mapping_config_path)
        self.test_instance = MidiReader(note_mapper)

    def test_sequence_extraction(self):
        self.test_instance.set_timing_quantization(NoteLength.SIXTEENTH)

        # Convert MIDI file to sequential text representation
        dataframe = self.test_instance.convert_to_dataframe(MIDI_FILE_7)

        print(dataframe.head(20).to_string())

        # TODO: assert something useful...
        self.assertTrue(True)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
