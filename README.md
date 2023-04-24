# Purdue Course Tracker

## Usage
1. Install Python
2. Create venv with `python -m venv venv`
3. Install deps with `pip install -r requirements.txt`
4. Edit `course_and_sections.py`'s `subjects` array to include the subjects you want to track
5. Run `python course_and_sections.py`, this will generate intermediate files
6. Create a file called `mycourses.json`, and put a list of courses you wanna track there. Example:
```json
[
    "CS 10100",
    "CS 10200"
]
```
7. If you wanna use Pushover, create a `tokens.json` file and put your app and ueer tokens there. Example:
```json
{
    "pushover-app": "app_token_here",
    "pushover-user": "user_token_here"
}
```
8. Run `python monitor_courses.py`, this will check for changes and send you a notification if there is one. It will also create a `temp.json` file which contains links to the page where you can check course availabilities.