import unittest

from midi_to_dataframe.note_mapper import NoteMapper
from midi_to_dataframe.midi_reader import MidiReader, NoteLength

MIDI_FILE_1 = "resources/midi/080 Downtempo 08.mid"
MIDI_FILE_2 = "resources/midi/090 New York.mid"
MIDI_FILE_3 = "resources/midi/135 Garage 02.mid"
MIDI_FILE_4 = "resources/midi/170 Jungle 09.mid"
MIDI_FILE_5 = "resources/midi/freestyler-clip.mid"
MIDI_FILE_6 = "resources/midi/Bomfunk_MCs_-_Freestyler.mid"
MIDI_FILE_7 = "resources/midi/Tool_-_The_grudge.mid"
MIDI_FILE_8 = "resources/midi/How Can You Mend a Broken Heart.1.mid"


class MidiReaderTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MidiReaderTests, self).__init__(*args, **kwargs)

        # Prepare tests objects
        note_mapping_config_path = "resources/config/map-to-group.json"
        note_mapper = NoteMapper(note_mapping_config_path)
        self.test_instance = MidiReader(note_mapper)

    def test_sequence_extraction(self):
        self.test_instance.set_timing_quantization(NoteLength.SIXTEENTH)

        # Convert MIDI file to sequential text representation
        dataframe = self.test_instance.convert_to_dataframe(MIDI_FILE_8)

        print(dataframe.head(20).to_string())

        # TODO: assert something useful...
        self.assertTrue(True)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
