import json
import copy
import random
import pandas as pd
import time
import requests
from threading import Thread
from bs4 import BeautifulSoup
import sys

with open("mycourses.json", "r") as f:
    my_course_numbers = json.load(f)

with open("tokens.json", "r") as f:
    tokens = json.load(f)


def send_push(message):
    print("=====================")
    print(message)
    print("=====================")

    token = tokens["pushover-app"]
    user = tokens["pushover-user"]
    url = "https://api.pushover.net/1/messages.json"
    headers = {"Content-Type": "application/json"}
    data = {
        "token": token,
        "user": user,
        "message": message,
    }

    r = requests.post(url, headers=headers, json=data)


send_push("Course monitor started.")

fetch_interval = 60

req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}


with open("courses.json", "r") as f:
    courses = json.load(f)

my_courses = []
for course in courses:
    for my_course_number in my_course_numbers:
        if my_course_number in course["number"]:
            my_courses.append(course)
            break

all_sections = []
for course in my_courses:
    for section in course["sections"]:
        section["course"] = course["number"]
        all_sections.append(section)


proxyPool = set()


def get_section_seating(section):
    r = requests.get(section["link"], headers=req_headers)

    if "sorry" in r.text:
        raise Exception(f"Rate limited for {section['link']}")

    soup = BeautifulSoup(r.text, "html.parser")

    caption = soup.find("caption", string="Registration Availability")
    if caption is None:
        print(section["link"])
        raise Exception("Could not find Registration Availability caption")

    table = caption.find_parent("table")
    df = pd.read_html(str(table), header=0, index_col=0)[0]

    seating = {
        "Seats": {
            "Capacity": df.loc["Seats", "Capacity"],
            "Actual": df.loc["Seats", "Actual"],
            "Remaining": df.loc["Seats", "Remaining"],
        },
        "Waitlist Seats": {
            "Capacity": df.loc["Waitlist Seats", "Capacity"],
            "Actual": df.loc["Waitlist Seats", "Actual"],
            "Remaining": df.loc["Waitlist Seats", "Remaining"],
        },
    }

    return seating


def diff_seating_pretty(prev, curr):
    section_title_full = f"{curr['course']}-{curr['name']}"

    if prev is None:
        return []

    try:
        if prev["seating"] == curr["seating"]:
            return []
    except KeyError:
        return []

    changes = []
    for seating_type in ["Seats", "Waitlist Seats"]:
        for key in ["Capacity", "Actual", "Remaining"]:
            try:
                if prev["seating"][seating_type][key] != curr["seating"][seating_type][key]:
                    changes.append(f"{section_title_full} {seating_type} {key} changed from {prev['seating'][seating_type][key]} to {curr['seating'][seating_type][key]}")
            except KeyError:
                pass

    return changes


def update_section_seating(section):
    try:
        print(f"Attempting to update {section['course']}-{section['name']}")
        section["seating"] = get_section_seating(section)

        return True
    except Exception as e:
        pretty_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{pretty_time}] {e}")

        return False


# from https://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread
class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


with open("temp.json", "w") as f:
    json.dump(all_sections, f)

prev_sections = []

dt = fetch_interval / len(all_sections)
while True:
    prev_sections = copy.deepcopy(all_sections)

    successes = 0
    total = 0
    for i in range(len(all_sections)):
        total += 1
        success = update_section_seating(all_sections[i])
        successes += success

        print(f"Section {all_sections[i]['name']} update {'success' if success else 'failure'}")

        if success:
            changes = diff_seating_pretty(prev_sections[i], all_sections[i])
            if len(changes) > 0:
                for change in changes:
                    print(change)
                    send_push(change)

        time.sleep(dt)

    print(f"{successes}/{total} successful updates")
