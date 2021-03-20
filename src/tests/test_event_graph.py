#!/usr/bin/env python

import unittest

from utils import events as events_graph


class TestEvents(unittest.TestCase):
    def test_event_graph(self):

        """
        Test the functionality of visaulizing several events as graph
        """

        # Single event
        events = [
            {
                "summary": "WORK",
                "start": {"dateTime": "2020-10-14T10:00:00+02:00", "timeZone": "UTC"},
                "end": {"dateTime": "2020-10-14T14:00:00+02:00", "timeZone": "UTC"},
            }
        ]
        self.assertEqual(
            events_graph.graph(events), "[]        WWWWWWWWWWWWWWWW            []"
        )

        # Two event
        events = [
            {
                "summary": "WORK",
                "start": {"dateTime": "2020-10-14T08:00:00+02:00", "timeZone": "UTC"},
                "end": {"dateTime": "2020-10-14T10:00:00+02:00", "timeZone": "UTC"},
            },
            {
                "summary": "WORK",
                "start": {"dateTime": "2020-10-14T14:00:00+02:00", "timeZone": "UTC"},
                "end": {"dateTime": "2020-10-14T15:00:00+02:00", "timeZone": "UTC"},
            },
        ]
        self.assertEqual(
            events_graph.graph(events), "[]WWWWWWWW                WWWW        []"
        )

        # Testing edge
        events = [
            {
                "summary": "WORK",
                "start": {"dateTime": "2020-10-14T10:07:31+02:00", "timeZone": "UTC"},
                "end": {"dateTime": "2020-10-14T14:00:00+02:00", "timeZone": "UTC"},
            }
        ]
        self.assertEqual(
            events_graph.graph(events), "[]         WWWWWWWWWWWWWWW            []"
        )

        events = [
            {
                "summary": "WORK",
                "start": {"dateTime": "2020-10-14T10:07:30+02:00", "timeZone": "UTC"},
                "end": {"dateTime": "2020-10-14T14:00:00+02:00", "timeZone": "UTC"},
            }
        ]
        self.assertEqual(
            events_graph.graph(events), "[]        WWWWWWWWWWWWWWWW            []"
        )


if __name__ == "__main__":
    unittest.main()