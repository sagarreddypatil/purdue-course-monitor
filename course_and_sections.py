from threading import Thread
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import requests
import json


term_selection = "Fall 2023"
subject_selections = ["CS", "ILS", "EAPS"]

base_url = "https://selfservice.mypurdue.purdue.edu"  # to append the links to

# load the cache
try:
    with open("cache.json", "r") as f:
        cache = json.load(f)
except FileNotFoundError:
    print("Cache not found")
    cache = None

# if cache exists and the term and subjects are the same, use the cache
if cache is not None and cache["term"] == term_selection and cache["subjects"] == subject_selections:
    print("Using cache")
    soup = BeautifulSoup(cache["source"], "html.parser")
else:
    driver = webdriver.Chrome()

    term_select_page = "https://selfservice.mypurdue.purdue.edu/prod/bwckctlg.p_disp_cat_term_date"
    driver.get(term_select_page)

    term_select_element = driver.find_element("id", "term_input_id")
    term_select = Select(term_select_element)

    term_select.select_by_visible_text(term_selection)

    # submit button with type submit
    button = driver.find_element("xpath", "//input[@type='submit']")
    button.click()

    subject_select_element = driver.find_element("id", "subj_id")
    subject_select = Select(subject_select_element)

    # select all the subjects in subject_select
    for subject in subject_selections:
        subject_select.select_by_value(subject)

    # now press the button with type submit
    button = driver.find_element("xpath", "//input[@type='submit']")
    button.click()

    # cache this to file, tag it with the term and subjects
    # so we don't have to do this every time
    dump_obj = {
        "term": term_selection,
        "subjects": subject_selections,
        "source": driver.page_source,
    }
    with open("cache.json", "w") as f:
        json.dump(dump_obj, f)

    soup = BeautifulSoup(driver.page_source, "html.parser")

courses = []

table = soup.find("table", {"class": "datadisplaytable"})
tbody = table.find("tbody")
for row in tbody.find_all("tr"):
    td = row.find("td")
    if td["class"][0] != "nttitle":
        continue

    link = td.find("a")
    course_number = link.text.split("-")[0].strip()
    course_title = link.text.split("-")[1].strip()
    course = {
        "number": course_number,
        "title": course_title,
        "link": base_url + link["href"],
    }

    courses.append(course)

req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}


def get_course_sections(course):
    try:
        r = requests.get(course["link"], headers=req_headers)
        soup = BeautifulSoup(r.text, "html.parser")

        links = []
        base_link = soup.find("a", string="All Sections for this Course")
        if base_link is not None:
            links.append(base_link)
        else:
            # get all the links on the line that has a span containing "Schedule Types", before the br
            # only the links on this line are the ones we want
            span = soup.find("span", string="Schedule Types: ")
            if span is None:
                return []

            for sibling in span.next_siblings:
                if sibling.name == "br":
                    break
                if sibling.name == "a":
                    links.append(sibling)

        sections = []

        for link in links:
            if link is None:
                continue

            link = base_url + link["href"]

            r = requests.get(link, headers=req_headers)
            soup = BeautifulSoup(r.text, "html.parser")

            table = soup.find("table", {"class": "datadisplaytable"})
            ths = table.find_all("th", {"class": "ddlabel"})

            for row in ths:
                # example "Systems Programming - 13335 - CS 25200 - L01"
                link = row.find("a")
                text_segments = link.text.split(" - ")

                section = {
                    "id": text_segments[1],
                    "name": text_segments[3],
                    "link": base_url + link["href"],
                }

                if section not in sections:
                    sections.append(section)

            return sections
    except Exception as e:
        print(e)
        return ["Failed"]


def add_sections_to_course(course):
    print(f"Starting {course['number']}")
    course["sections"] = get_course_sections(course)
    print(f"Finished {course['number']}")


threads = []
for course in courses:
    t = Thread(target=add_sections_to_course, args=(course,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

# dump courses to file
with open("courses.json", "w") as f:
    json.dump(courses, f)
    print("Dumped courses to file")
