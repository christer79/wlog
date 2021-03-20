from __future__ import print_function
import datetime

import datetime
import pytz
import sys
import math
import argparse
import yaml
from string import Template


def time_in_range(x, start, end):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def format_event(event):
    start = get_datetime(event, "start")
    end = get_datetime(event, "end")
    duration = format_time_diff(event_duration(event).total_seconds(), plus_sign="")
    description = ""
    try:
        description = event["description"]
    except KeyError:
        pass
    return "{} {}-{} ({}) {} [{}] : {}".format(
        start.date(),
        start.time(),
        end.time(),
        duration,
        event["summary"],
        event["id"],
        description,
    )


def print_events(events):
    for event in events:
        print(format_event(event))


def get_datetime(event, entity):
    start = datetime.datetime.strptime(
        event[entity].get("dateTime", event[entity].get("date")), "%Y-%m-%dT%H:%M:%S%z"
    )
    return start


def get_events_on_date(all_events, date):
    events = []
    for event in all_events:
        start = get_datetime(event, "start").date()
        if start == date:
            events.append(event)
    return events


def graph(
    events,
    start=datetime.time(8, 0, 0),
    end=datetime.time(17, 0, 0),
    resolution=datetime.timedelta(minutes=15),
):

    dt = datetime.datetime(100, 1, 1)
    range_start = datetime.datetime.combine(dt, start)
    range_end = datetime.datetime.combine(dt, end)

    time_histogram = []

    entry = range_start + resolution / 2.0
    while entry < range_end + resolution / 2.0:
        time_histogram.append(entry)
        entry += resolution

    ret_val = "[]"
    for t in time_histogram:
        inside = False
        for event in events:
            event_start = dt.combine(dt, get_datetime(event, "start").time())
            event_end = dt.combine(dt, get_datetime(event, "end").time())
            if time_in_range(t, event_start, event_end):
                inside = True
                break
        if inside:
            ret_val += event["summary"][0:1]
        else:
            ret_val += " "

    return ret_val + "[]"
