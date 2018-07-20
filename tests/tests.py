import unittest

from midi_to_dataframe import NoteMapper, MidiReader

MIDI_FILE_1 = "resources/midi/Bomfunk_MCs_-_Freestyler.mid"


class MidiReaderTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(MidiReaderTests, self).__init__(*args, **kwargs)

        # Prepare tests objects
        note_mapping_config_path = "resources/config/map-to-group.json"
        note_mapper = NoteMapper(note_mapping_config_path)
        self.reader = MidiReader(note_mapper)

    def test_sequence_extraction(self):
        self.reader.set_extract_timestamp(False)
        self.reader.set_extract_time_signature(False)

        # Convert MIDI file to sequential text representation
        dataframe = self.reader.convert_to_dataframe(MIDI_FILE_1)
        self.assertTrue(dataframe.shape[0] > 0)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
