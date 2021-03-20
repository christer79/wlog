#!/usr/bin/env python

from __future__ import print_function
import datetime
import pytz
from pytz import timezone
import pickle
import os.path
import csv
import sys
import math
import argparse
import yaml
from string import Template


from cal import get_all_events, get_calendar_id, authenticate

# If modifying these scopes, delete the file token.pickle.
FULLDAYOFFS = ["VACATION", "6JULYCOMPENSATION",
               "FURLOUGH", "NATIONAL HOLIDAY", "HOLLIDAY"]
IGNORED = ["JOUR", "COMPENSATION"]


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    YELLOW = '\033[93m'
    WEEKEND = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class WorkHours:
    def __init__(self, service, config, args):
        self.expected_work_hours = config["expected"]
        self.args = args
        self.service = service

    def planned(self, date):
        for expected_work_time in self.expected_work_hours:
            exp_date = datetime.datetime.strptime(
                expected_work_time["startdate"], "%Y-%m-%d").date()
            if exp_date < date:
                return datetime.timedelta(hours=expected_work_time["hours"][date.weekday()])
        return datetime.timedelta(hours=7, minutes=12)

    def total_worktime(self, events):
        duration = datetime.timedelta()
        for event in events:
            if event["summary"] in FULLDAYOFFS:
                duration = duration + \
                    self.planned(get_datetime(event, "start").date())
            elif event["summary"] not in IGNORED:
                duration = duration + event_duration(event)
        return duration

    def day_summary(self):
        today = datetime.datetime.now().date()
        calendar_id = get_calendar_id(self.service, self.args.calendar)
        all_events = get_all_events(self.service, calendar_id)
        events_on_day = get_events_on_date(all_events, today)
        total_worktime = self.total_worktime(events_on_day)
        print(f"\nTotal time worked today: {total_worktime}/{self.planned(today)}",
              format_time_diff(time_diff(total_worktime, self.planned(today))))

    def summary(self):
        calendar_id = get_calendar_id(self.service, self.args.calendar)
        all_events = get_all_events(self.service, calendar_id)

        # The size of each step in days
        day_delta = datetime.timedelta(days=1)

        start_date = self.args.start.date()
        first_date = get_first_date(all_events).date()
        if start_date < first_date:
            start_date = first_date
        end_date = self.args.end.date()

        acc_time_diff_total = 0.0
        acc_time_diff_week = 0.0
        acc_time_diff_month = 0.0

        for i in range((end_date - start_date).days + 1):
            date = start_date + i*day_delta
            if date.weekday() == 0:
                if self.args.weeks:
                    print(" ** WEEK {} SUMMARY: ".format((date-day_delta).isocalendar()
                                                         [1]) + format_time_diff(acc_time_diff_week))
                acc_time_diff_week = 0.0
            if date.day == 1:
                if self.args.months:
                    print(" **** {} SUMMARY: ".format((date-day_delta).strftime("%B")
                                                      ) + format_time_diff(acc_time_diff_month))
                acc_time_diff_month = 0.0

            day_events = get_events_on_date(all_events, date)
            worktime = self.total_worktime(day_events)
            acc_time_diff_total += time_diff(worktime, self.planned(date))
            acc_time_diff_week += time_diff(worktime, self.planned(date))
            acc_time_diff_month += time_diff(worktime, self.planned(date))
            if self.args.days:
                color = ""
                if date.weekday() == 5 or date.weekday() == 6:
                    color = bcolors.WEEKEND
                print(color, date, format_timedelta(worktime), format_time_diff(time_diff(worktime, self.planned(date))), events_graph(day_events, start=datetime.time(
                    0, 0, 0), end=datetime.time(23, 59, 59), resolution=datetime.timedelta(minutes=15)), bcolors.ENDC, format_time_diff(acc_time_diff_total))
        print("Total: " + format_time_diff(acc_time_diff_total))


def time_in_range(x, start, end):
    """Return true if x is in the range [start, end]"""
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


def events_graph(events, start=datetime.time(8, 0, 0), end=datetime.time(17, 0, 0), resolution=datetime.timedelta(minutes=15)):

    dt = datetime.datetime(100, 1, 1)
    range_start = datetime.datetime.combine(dt, start)
    range_end = datetime.datetime.combine(dt, end)

    time_histogram = []

    entry = range_start+resolution/2.0
    while entry < range_end+resolution/2.0:
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

    return ret_val+"[]"


def event_duration(event):
    return datetime.datetime.fromisoformat(event['end'].get('dateTime'))-datetime.datetime.fromisoformat(event['start'].get('dateTime'))


def format_event(event):
    start = get_datetime(event, "start")
    end = get_datetime(event, "end")
    duration = format_time_diff(event_duration(
        event).total_seconds(), plus_sign="")
    description = ""
    try:
        description = event["description"]
    except KeyError:
        pass
    return "{} {}-{} ({}) {} [{}] : {}".format(start.date(), start.time(), end.time(), duration, event['summary'], event['id'], description)


def print_events(events):
    for event in events:
        print(format_event(event))


def generate_event(start, end, summary, description, location):
    utc = pytz.timezone("UTC")
    utc_start = start.astimezone(utc)
    utc_end = end.astimezone(utc)
    return {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': utc_start.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': utc_end.isoformat(),
            'timeZone': 'UTC',
        },
        'recurrence': [
        ],
        'attendees': [
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [

            ],
        },
    }


def create_new_event(service, event, args):
    calendar_id = get_calendar_id(service, args.calendar)
    event = service.events().insert(calendar_id=calendar_id, body=event).execute()
    print('Event created: %s' % (event.get('htmlLink')))


# Used once to import old data from a csv file. Will not be maintained
def read_old_times(filename):
    # Used to load old events from csv file into calendar

    # psql  -h localhost -p 5433 -U postgres -d timetracker -c "SELECT * from events_lvmz7swguxyw2x8655rfbkbeizy1;" > times_from_before.csv
    # cat times_from_before.csv | sed s/\ *\|/\|/g > times_from_before.csv_

    # old_events=read_old_times('times_from_before.csv_')
    # for event in old_events:
    #     print(event)
    #     create_new_event(service,event)

    utc = pytz.timezone("UTC")
    events = []
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|', skipinitialspace=True)
        for row in reader:
            print("*****")
            print(row['starttime'], row['endtime'],
                  row['project'], row['description'])
            if row['starttime']:
                if row['description'] and row['description'].isupper():
                    summary = row['description']
                    description = row['description']
                else:
                    summary = "WORK"
                    description = row['description']
                start_time = datetime.datetime.strptime(
                    row['starttime']+" UTC", "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=utc).astimezone(tz=None)
                end_time = datetime.datetime.strptime(
                    row['endtime']+" UTC", "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=utc).astimezone(tz=None)
                print(start_time, end_time, summary, description)
                print(generate_event(start_time, end_time, summary, description, ""))
                events.append(generate_event(
                    start_time, end_time, summary, description, ""))
    return events


def start(args, service, wh):
    ongoing_events = find_ongoing_events(service, args)
    if len(ongoing_events) > 0:
        print("There are {} ongoing evnts, consider stopping them before starting new.")
        for event in ongoing_events:
            print(format_event(event))
        if len(ongoing_events) == 1:
            if query_yes_no("Stop the ongoing event at this time", default="no"):
                utc = pytz.timezone("UTC")
                event = ongoing_events[0]
                end_time = datetime.datetime.combine(
                    args.date.date(), args.start.time())
                utc_end = end_time.astimezone(utc)
                event["end"]["dateTime"] = utc_end.isoformat()
                calendar_id = get_calendar_id(service, args.calendar)
                updated_event = service.events().update(
                    calendar_id=calendar_id, eventId=event['id'], body=event).execute()
                print(updated_event['updated'])
        else:
            if not args.force and not query_yes_no("Start event anyway", default="no"):
                sys.exit(0)

    start_time = datetime.datetime.combine(args.date.date(), args.start.time())
    event = generate_event(start_time, start_time,
                           args.summary, args.description, args.location)
    create_new_event(service, event, args)


def stop(args, service, wh):
    calendar_id = get_calendar_id(service, args.calendar)
    # Find latest event with same start and stop time
    possible_events = find_ongoing_events(service, args)

    if len(possible_events) == 1:
        event = possible_events[0]
    else:
        print("None or too many event were found: ", len(possible_events))
        sys.exit(1)

    # Show suggested event
    print("Event to update:")
    print(format_event(event))

    # Confirm update
    if args.force or query_yes_no("Stop that event", "no"):
        # Update event
        new_event = patch_event(event, args)
        updated_event = service.events().update(
            calendar_id=calendar_id, eventId=new_event['id'], body=new_event).execute()
        print(updated_event['updated'])


def find_ongoing_events(service, args):
    calendar_id = get_calendar_id(service, args.calendar)
    all_events = get_all_events(service, calendar_id)
    possible_events = []
    for event in all_events:
        if event_duration(event).total_seconds() == 0.0:
            possible_events.append(event)
    return possible_events


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def update_event(event, service, args):
    calendar_id = get_calendar_id(service, args.calendar)
    updated_event = service.events().update(
        calendar_id=calendar_id, eventId=event['id'], body=event).execute()
    print(updated_event['updated'])


def patch_event(event, args):
    utc = pytz.timezone("UTC")
    if args.date:
        try:
            if args.start:
                start_time = datetime.datetime.combine(
                    args.date.date(), args.start.time())
                utc_start = start_time.astimezone(utc)
                event["start"]["dateTime"] = utc_start.isoformat()
        except AttributeError:
            pass

        if args.end:
            end_time = datetime.datetime.combine(
                args.date.date(), args.end.time())
            utc_end = end_time.astimezone(utc)
            event["end"]["dateTime"] = utc_end.isoformat()

    if args.description:
        event["description"] = args.description
    if args.summary:
        event["summary"] = args.summary
    if args.location:
        event["location"] = args.location

    return event


def update(args, service, wh):
    calendar_id = get_calendar_id(service, args.calendar)
    event = service.events().get(calendar_id=calendar_id, eventId=args.id).execute()
    print("Replace event")
    print(format_event(event))
    print("with:")
    new_event = patch_event(event, args)
    print(new_event)
    if args.force or query_yes_no("Update the above evetn?", default="no"):
        update_event(new_event, service, args)


def create(args, service, wh):
    start_time = datetime.datetime.combine(args.date.date(), args.start.time())
    end_time = datetime.datetime.combine(args.date.date(), args.end.time())
    event = generate_event(start_time, end_time,
                           args.summary, args.description, args.location)
    create_new_event(service, event, args)


def filter_events(events, start, end):
    ret_events = []
    for event in events:
        event_start = get_datetime(event, "start")
        if event_start.date() >= start.date() and event_start.date() <= end.date():
            ret_events.append(event)
    return ret_events


def list(args, service, wh):
    calendar_id = get_calendar_id(service, args.calendar)
    all_events = get_all_events(service, calendar_id)
    events = filter_events(all_events, args.start, args.end)
    print_events(events)


def delete(args, service, wh):
    for id in args.ids:
        calendar_id = get_calendar_id(service, args.calendar)
        event = service.events().get(calendar_id=calendar_id, eventId=id).execute()
        print("Delete event")
        print(format_event(event))
        if args.force or query_yes_no("Delete the above evetn?", default="no"):
            service.events().delete(calendar_id=calendar_id, eventId=id).execute()


def get_first_date(all_events):
    utc = pytz.utc
    earliest_date = utc.localize(datetime.datetime.utcnow())
    for event in all_events:
        start = datetime.datetime.strptime(event['start'].get(
            'dateTime', event['start'].get('date')), "%Y-%m-%dT%H:%M:%S%z")
        if earliest_date > start:
            earliest_date = start
    return earliest_date


def get_datetime(event, entity):
    start = datetime.datetime.strptime(event[entity].get(
        'dateTime', event[entity].get('date')), "%Y-%m-%dT%H:%M:%S%z")
    return start


def get_events_on_date(all_events, date):
    events = []
    for event in all_events:
        start = get_datetime(event, "start").date()
        if start == date:
            events.append(event)
    return events


class DeltaTemplate(Template):
    delimiter = "%"


def format_timedelta(tdelta, fmt='%H:%M:%S'):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def format_time_diff(diff_seconds, plus_sign="+"):
    if diff_seconds > 0.0:
        sign = +1
        sign_str = plus_sign
    else:
        sign = -1
        sign_str = "-"
    diff_seconds = diff_seconds * sign
    hours = math.floor(diff_seconds // 3600)
    diff_seconds %= 3600
    minutes = math.floor(diff_seconds // 60)
    diff_seconds %= 60
    seconds = math.floor(diff_seconds)
    WARN = ""
    if hours > 3:
        WARN = "<"
    else:
        WARN = " "

    return "{}{:02d}:{:02d}:{:02d} {}".format(sign_str, hours, minutes, seconds, WARN)


def time_diff(actual_worktime, expected_worktime):
    diff_seconds = actual_worktime.total_seconds() - expected_worktime.total_seconds()
    return diff_seconds


def summary(args, service, wh):
    wh.summary()


DATE_FORMAT = '%Y-%m-%d'


def main():

    parser = argparse.ArgumentParser(
        description='Interact append s with a google calendar to log work time.\n\n')

    parser.add_argument(
        '-c', '--calendar', help="Which Calendar to work with", default="Work Hours")
    parser.add_argument('-f', '--force', dest='force', action='store_true')

    subparsers = parser.add_subparsers()

    parser_add = subparsers.add_parser('create')
    parser_add.add_argument('-d', '--date', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime.now(),
                            help='End time for event')
    parser_add.add_argument('-s', '--start', type=lambda s: datetime.datetime.strptime(s, '%H:%M'),
                            help='Start time for event')
    parser_add.add_argument('-e', '--end', type=lambda s: datetime.datetime.strptime(s, '%H:%M'),
                            help='End time for event')
    parser_add.add_argument('-S', '--summary', default="WORK",
                            help='Summary of event')
    parser_add.add_argument('-D', '--description', default="",
                            help='Description of event')
    parser_add.add_argument('-l', '--location', default="",
                            help='Location of event')
    parser_add.set_defaults(func=create)

    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('-d', '--date', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT),
                               help='End time for event', default=None)
    parser_update.add_argument('-s', '--start', type=lambda s: datetime.datetime.strptime(s, '%H:%M'),
                               help='Start time for event', default=None)
    parser_update.add_argument('-e', '--end', type=lambda s: datetime.datetime.strptime(s, '%H:%M'),
                               help='End time for event', default=None)
    parser_update.add_argument('-S', '--summary', default=None,
                               help='Summary of event')
    parser_update.add_argument('-D', '--description', default=None,
                               help='Description of event')
    parser_update.add_argument('-l', '--location', default=None,
                               help='Location of event')
    parser_update.add_argument(
        '-i', '--id', help="eventId of event to be removed")
    parser_update.set_defaults(func=update)

    parser_start = subparsers.add_parser('start')
    parser_start.add_argument('-d', '--date', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime.now(),
                              help='End time for event')
    parser_start.add_argument('-s', '--start', type=lambda s: datetime.datetime.strptime(s, '%H:%M'), default=datetime.datetime.now(),
                              help='Start time for event')
    parser_start.add_argument('-S', '--summary', default="WORK",
                              help='Summary of event')
    parser_start.add_argument('-D', '--description', default="",
                              help='Description of event')
    parser_start.add_argument('-l', '--location', default="",
                              help='Location of event')
    parser_start.set_defaults(func=start)

    parser_stop = subparsers.add_parser('stop')
    parser_stop.add_argument('-d', '--date', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime.now(),
                             help='End time for event')
    parser_stop.add_argument('-e', '--end', type=lambda s: datetime.datetime.strptime(s, '%H:%M'), default=datetime.datetime.now(),
                             help='Stop time for event')
    parser_stop.add_argument('-S', '--summary', default=None,
                             help='Summary of event')
    parser_stop.add_argument('-D', '--description', default=None,
                             help='Description of event')
    parser_stop.add_argument('-l', '--location', default=None,
                             help='Location of event')
    parser_stop.set_defaults(func=stop)

    parser_delete = subparsers.add_parser('delete')
    parser_delete.add_argument('ids', nargs=argparse.REMAINDER)
    parser_delete.set_defaults(func=delete)

    parser_list = subparsers.add_parser('list')
    parser_list.add_argument('-s', '--start', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime(1970, 1, 1),
                             help='Start time for event')
    parser_list.add_argument('-e', '--end', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime.now(),
                             help='End time for event')
    parser_list.set_defaults(func=list)

    parser_summary = subparsers.add_parser('summary')
    parser_summary.add_argument('-s', '--start', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime(1970, 1, 1),
                                help='Start time for event')
    parser_summary.add_argument('-e', '--end', type=lambda s: datetime.datetime.strptime(s, DATE_FORMAT), default=datetime.datetime.now(),
                                help='End time for event')
    parser_summary.add_argument('-d', '--days', action='store_true')
    parser_summary.add_argument('-w', '--weeks', action='store_true')
    parser_summary.add_argument('-m', '--months', action='store_true')
    parser_summary.set_defaults(func=summary)

    args = parser.parse_args()

    with open("work-hours.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)

    service = authenticate()
    wh = WorkHours(service, config, args)

    args.func(args, service, wh)
    wh.day_summary()


if __name__ == '__main__':
    main()
