import json
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup

with open("mycourses.json", "r") as f:
    my_course_numbers = json.load(f)

fetch_interval = 10  # seconds

req_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
}


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
                    changes.append(
                        f"{section_title_full} {seating_type} {key} changed from {prev['seating'][seating_type][key]} to {curr['seating'][seating_type][key]}"
                    )
            except KeyError:
                pass

    return changes


prev_sections = list(all_sections)

while True:
    prev_sections = list(all_sections)
    prev_sections[1]["seating"] = get_section_seating(prev_sections[0])
    prev_sections[1]["seating"]["Seats"]["Remaining"] = 123

    for section in all_sections:
        try:
            section["seating"] = get_section_seating(section)
        except Exception as e:
            print(e)
            break

    for prev, curr in zip(prev_sections, all_sections):
        changes = diff_seating_pretty(prev, curr)
        if len(changes) > 0:
            for change in changes:
                print(change)

    time.sleep(fetch_interval)
