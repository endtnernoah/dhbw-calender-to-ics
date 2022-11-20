import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
from dataclasses import dataclass
from ics import Calendar, Event
from datetime import datetime, date, timedelta

# Default vars
url = ""

# Save course data 
@dataclass(init=True, frozen=True)
class Course():
    title: str
    location: str
    id: str
    start_time: str
    end_time: str
    date: str

# Convert the calendar table into a list of Course objects
def get_calendar_data(url: str = None) -> list:
    if url is None or url == "":
        raise AssertionError("Missing parameter: 'url'")

    all_courses = []

    # Get calendar data
    r = requests.get(url)
    if r.status_code >= 300:
        raise HTTPError(f"Getting calendar data failed with {r.status_code} {r.reason}: {r.text}")

    # Init bs4 object
    soup = BeautifulSoup(r.text, "html.parser")

    # Iterate over all weeks
    weeks = soup.find_all("div", {"class": "calendar"})
    for index, week in enumerate(weeks):
        dates = [date.text for date in week.find_all('td', {'class': 'week_header'})]
        
        # Iterate over all tables except the first two cause they only contain the dates and a spacer
        for tablerow in list(week.find_all('tr'))[2:]:

            # Continue if there are no courses in this row
            courses = tablerow.find_all('td', {'class': ['week_block']})
            if len(courses) == 0:
                continue
            cells = tablerow.find_all('td')
            index = -1

            # Increase index on spacer cells to account for courses overlapping into row below
            for cell in cells:
                if "week_smallseparatorcell_black" in cell["class"] or "week_smallseparatorcell" in cell["class"]:
                    index += 1
                
                # Only parse courses, not empty cells
                if not "week_block" in cell["class"]:
                    continue
                
                
                # Easier naming
                course = cell
    
                # Get date from header
                course_date = dates[index]

                # Get other data
                course_time = course.find("a").text[:12]
                course_start_time, course_end_time = course_time.split(" -")
                course_title = course.find("a").text[12:]

                # Some courses dont have an id, check for that
                try:
                    course_id = course.find_all("span")[0].text
                except IndexError:
                    course_id = ""

                # Some courses dont have a location, check for that
                try:
                    course_location = course.find_all("span")[1].text
                except IndexError:
                    course_location = ""

                # Create course object and append it to the list
                course_obj = Course(title=course_title, location=course_location, id=course_id, start_time=course_start_time, end_time=course_end_time, date=course_date)
                all_courses.append(course_obj)
        
    return all_courses

# Format the list of courses to a ICS file
def format_to_ics(ics_file: str = None, data: list = None) -> None:
    # Save year to detect year wraparound because the calendar does not include the year
    today = date.today()
    year = today.year

    # Prev month to detect year wrapping
    prev_month = data[0].date.strip(".").split(".")[1]

    c = Calendar()
    for course in data:
        
        # Parse month from course obj
        cur_month = course.date.strip(".").split(".")[1]
        cur_day = course.date.strip(".").split(".")[0].split(" ")[1]
        
        # Wrap around year if month is 11 smaller
        if int(prev_month) - int(cur_month) == 11:
            print("Detected year change with " + str(course))
            year += 1

        # Create datetime objects
        start_timestamp = datetime.strptime(f"{year}-{cur_month}-{cur_day} {course.start_time}:00", "%Y-%m-%d %H:%M:%S")
        end_timestamp = datetime.strptime(f"{year}-{cur_month}-{cur_day} {course.end_time}:00", "%Y-%m-%d %H:%M:%S")
        
        # Initialize ICS Event with name and location 
        e = Event()
        e.name = course.title
        e.location = course.location
        
        # Convert timestamps from GMT+1 to GMT
        e.begin = start_timestamp - timedelta(hours=1)
        e.end = end_timestamp - timedelta(hours=1)

        # Add new event to calendar
        c.events.add(e)

        # Resetting to detect year changes
        prev_month = cur_month

    # Write the new calendar to the ICS file
    with open(ics_file, "w") as f:
        f.writelines(c.serialize_iter())
 
# Main
if __name__ == "__main__": 
    format_to_ics("courses.ics", get_calendar_data(url))