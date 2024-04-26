import python3_midi

REST = "rest"
PERCUSSION = "percussion"
PERCUSSION_CHANNEL = 9
DEFAULT_MIDI_RESOLUTION = 120
DEFAULT_MIDI_BPM = 120


class MidiWriter(object):
    """
    Interface for writing data to MIDI files.
    """

    def __init__(self, note_mapper):
        """
        Creates a new MidiWriter instance.
        :return: None.
        """

        # Note mapping configuration to use
        self._note_mapper = note_mapper

        # MIDI file resolution (ticks per quarter note)
        self._resolution = DEFAULT_MIDI_RESOLUTION

        # MIDI tempo
        self._bpm = DEFAULT_MIDI_BPM

        # Intermediary data stores for tracks, program names and timestamps
        self._midi_tracks_by_track_num = {}
        self._prog_names_by_track_num = {}
        self._prev_timestamps_by_track_num = {}

    def convert_to_midi(self, dataframe, save_to_path):
        """
        Converts a (properly-formed) Pandas Data Frame into a MIDI file and writes it to disk.
        :param dataframe: the Pandas Data Frame to convert.
        :param save_to_path: the path to write the MIDI file to.
        :return: None.
        """
        pattern = python3_midi.Pattern()
        pattern.resolution = self._resolution

        # Reset all internal state variables to their defaults
        self._resolution = DEFAULT_MIDI_RESOLUTION
        self._bpm = DEFAULT_MIDI_BPM
        self._midi_tracks_by_track_num = {}
        self._prog_names_by_track_num = {}
        self._prev_timestamps_by_track_num = {}

        # Select average BPM of dataframe as output BPM
        # TODO handle tempo changes throughout the song
        if 'bpm' in dataframe.columns:
            self._bpm = dataframe['bpm'].mean()

        # Explicitly add drum track on channel 9
        self._add_track(PERCUSSION_CHANNEL, PERCUSSION, pattern)
        self._prog_names_by_track_num[PERCUSSION_CHANNEL] = PERCUSSION

        # Extract notes from each row of the dataframe and record the events to be added
        midi_events_by_timestamp = {}
        for index, row in dataframe.iterrows():

            # Each row should represent one 16th note
            # (which is one quarter of the MIDI resolution)
            # TODO: make this configurable
            current_timestamp = int(index * (self._resolution / 4))

            # Note "words" are stored in the 'notes' column
            note_words = row['notes'].split(",")
            for note_word in note_words:
                if note_word != REST:

                    # TODO replace underscore with constant/variable from note_mapping
                    fields = note_word.split("_")

                    # TODO handle customized note fields
                    program_name = fields[0]
                    note_name = fields[1]
                    note_duration = fields[2]

                    # Check if program_name has already been encountered
                    if program_name not in self._prog_names_by_track_num.values():
                        # If not, create a MIDI track for it
                        program_index = self._get_next_unused_track(self._prog_names_by_track_num)
                        if program_index >= 0:
                            self._prog_names_by_track_num[program_index] = program_name
                            self._add_track(program_index, program_name, pattern)

                    # Get MIDI track for this program
                    (track_num, midi_track) = self._get_midi_track(program_name)
                    if midi_track is not None:

                        # Add NoteOn event to events to be added
                        key = self._note_mapper.get_note_number(note_name)
                        on_event = python3_midi.NoteOnEvent(velocity=127, pitch=key, channel=track_num)
                        if current_timestamp in midi_events_by_timestamp:
                            events = midi_events_by_timestamp[current_timestamp]
                            events.append(on_event)
                        else:
                            events = [on_event]
                        midi_events_by_timestamp[current_timestamp] = events

                        # Add NoteOff event to events to be added
                        off_event = python3_midi.NoteOffEvent(pitch=key, channel=track_num)
                        off_timestamp = current_timestamp + int((float(note_duration) * self._resolution))
                        if off_timestamp in midi_events_by_timestamp:
                            events = midi_events_by_timestamp[off_timestamp]
                            events.append(off_event)
                        else:
                            events = [off_event]
                        midi_events_by_timestamp[off_timestamp] = events

        # Add actual MIDI events to pattern
        for timestamp in sorted(midi_events_by_timestamp):
            events = midi_events_by_timestamp[timestamp]
            for event in events:
                track_num = event.channel
                prev_timestamp = self._prev_timestamps_by_track_num[track_num]
                delta = timestamp - prev_timestamp
                event.tick = delta
                midi_track = self._midi_tracks_by_track_num[event.channel]
                midi_track.append(event)
                self._prev_timestamps_by_track_num[track_num] = timestamp

        # Add End-of-track event to every MIDI track
        for track_num, midi_track in self._midi_tracks_by_track_num.items():
            midi_track.append(python3_midi.EndOfTrackEvent(tick=1))

        # Write MIDI file to disk
        python3_midi.write_midifile(save_to_path, pattern)

    def _get_midi_track(self, program_name):
        """
        Returns the index and MIDI track for a given MIDI program name.
        :param program_name: the program name to look up.
        :return: a tuple: (track number, MIDI track) for the program name, or None if none was found.
        """
        if program_name not in self._prog_names_by_track_num.values():
            return None
        track_num = list(self._prog_names_by_track_num.keys())[
            list(self._prog_names_by_track_num.values()).index(program_name)]
        return track_num, self._midi_tracks_by_track_num[track_num]

    def _add_track(self, track_index, program_name, pattern):
        """
        Creates a new track in the designated MIDI pattern at the given track index and program name.
        :param track_index: the track number to use.
        :param program_name: the program name to use.
        :param pattern: the MIDI pattern to append the track to.
        :return: None.
        """
        track = python3_midi.Track()
        if program_name == PERCUSSION:
            # Set general track information on percussion channel

            # TODO: Set time signature information:
            # time_signature_event = midi.TimeSignatureEvent(tick=0)
            # time_signature_event.set_numerator(4)
            # time_signature_event.set_denominator(4)
            # time_signature_event.set_metronome(24)
            # time_signature_event.set_thirtyseconds(8)
            # track.append(time_signature_event)

            # Set tempo (BPM)
            tempo_event = python3_midi.SetTempoEvent(tick=0, bpm=int(self._bpm))
            track.append(tempo_event)

            # Set drum channel
            track.append(python3_midi.ProgramChangeEvent(tick=0, channel=PERCUSSION_CHANNEL))
        else:
            program_num = self._note_mapper.get_program_number(program_name)
            program_change_event = python3_midi.ProgramChangeEvent(tick=0, data=[program_num])
            track.append(program_change_event)

        pattern.append(track)
        self._midi_tracks_by_track_num[track_index] = track
        self._prev_timestamps_by_track_num[track_index] = 0

    @staticmethod
    def _get_next_unused_track(tracks):
        """
        Gets the lowest unused track number from the given list of MIDI tracks.
        :param tracks: the collection of MIDI tracks already in use.
        :return: the lowest track number available, up to channel 16 or -1 if no unused track numbers are left.
        """
        for track_index in range(0, 16):
            if track_index not in tracks:
                return track_index
        return -1
