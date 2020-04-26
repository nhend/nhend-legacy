"""
Ducktracker Conversion Script

Converts a given .json file to a tab delineated text file as specified by
system requirement 6
"""

from datetime import datetime
from urllib import request
import tkinter as tk
from tkinter import filedialog
import json
from statistics import mode
from random import randint

# Global temporal sampling interval in minutes
TSI = 5


def find_home(data, user) -> (str, str):
    """
    Returns a lat/lon tuple of the user's most frequent location, assumed to
    be their home.

    :param data: JSON object
    :param user: JSON object
    :return: Tuple containing latitude/longitude coordinates
    """
    latlons = []

    # Iterate through all of user's location measurement entries
    for entry in data[user]:
        lat = data[user][entry]['latitude']
        lon = data[user][entry]['longitude']

        # If latitude or longitude is blank, ignore and don't write to file
        if lat == "" or lon == "":
            continue

        # Reduce to 4 decimal places to reduce threshold for accuracy
        lat = '%.4f' % float(lat)
        lon = '%.4f' % float(lon)
        latlons.append((lat, lon))

    # Find most frequent location
    try:
        home_latlon = mode(latlons)
    # If there are multiple with the same frequency, the user has not been using
    # the app long enough to make an accurate determination so we guess the 0th
    except:
        home_latlon = latlons[0]

    return str(home_latlon[0]), str(home_latlon[1])


def within_tsi(before_date, before_time, after_date, after_time) -> bool:
    """
    Returns an a boolean representing the relationship between two datetime
    measurements. If the elapsed time between the measurements is greater than
    the margin of 2*TSI (in seconds), False is returned. If it is within the
    margin, True is returned.

    :param before_date: Date string in MM/DD/YYYY format
    :param before_time: Time string in HH:MM:SS format
    :param after_date: Date string in MM/DD/YYYY format
    :param after_time: Time string in HH:MM:SS format
    :return: Boolean
    """
    fmt = "%m/%d/%Y-%H:%M:%S"
    before = datetime.strptime(before_date + "-" + before_time, fmt)
    after = datetime.strptime(after_date + "-" + after_time, fmt)
    delta = (after - before).total_seconds()

    return delta <= TSI * 60 * 2


def is_same_place(latlon_1, latlon_2) -> bool:
    """
    Given two coordinates, determines if they are practically the same location
    (within a margin).

    :param latlon_1: Tuple containing latitude/longitude coordinates
    :param latlon_2: Tuple containing latitude/longitude coordinates
    :return: Boolean
    """

    # Equivalent to about 70ft
    margin = .0002

    same_lat = abs(float(latlon_1[0]) - float(latlon_2[0])) <= margin
    same_lon = abs(float(latlon_1[1]) - float(latlon_2[1])) <= margin

    return same_lat and same_lon


def write_out(data, out_filename="ducktracker_output.txt") -> None:
    """
    Opens and extracts contents of a json file by the given filename and
    writes contents out to a .txt file using tabs for delimiters. Also
    calculates time at location with the granularity allowed by the TSI.

    :param data: JSON object
    :param out_filename: Desired name/location of output .txt file (optional)
    :return: None
    """

    out = open(out_filename, "w+")
    out.write("User I.D.\tDate\tTime\tLatitude\tLongitude\tTime at Location\n")

    for user in data:
        time_at_loc = 0
        prev_time = ""
        prev_date = ""
        prev_latlon = (-1, -1)

        home_latlon = find_home(data, user)
        anon_home_lat = home_latlon[0][:-1] + str(randint(0, 9))
        anon_home_lon = home_latlon[1][:-1] + str(randint(0, 9))

        # Iterate through all of user's location measurement entries
        for entry in data[user]:
            lat = data[user][entry]['latitude']
            lon = data[user][entry]['longitude']

            # If latitude or longitude is blank, ignore and don't write to file
            if lat == "" or lon == "":
                continue

            # Remove space, separate date/time with tabs, append to string
            date, time = entry.split(" ", 1)
            year, month, day = date.split("-")
            date = "/".join([month, day, year])

            # This is the safest way I thought of to ensure 4 sig. figures
            lat = '%.4f' % float(lat)
            lon = '%.4f' % float(lon)

            # Current lat/lon matches previous, add the TSI to location time
            if is_same_place((lat, lon), prev_latlon):
                if within_tsi(prev_date, prev_time, date, time):
                    time_at_loc += TSI
                else:
                    time_at_loc = 0
            # User is in a new location -- reset location time
            else:
                time_at_loc = 0
                prev_latlon = (lat, lon)

            prev_time = time
            prev_date = date

            # If home location, anonymize
            if is_same_place((lat, lon), home_latlon):
                lat = anon_home_lat
                lon = anon_home_lon

            # Tab delimiting
            s = "\t".join([user, date, time, lat, lon, str(time_at_loc)]) + '\n'
            out.write(s)

    out.close()


def pick_output():
    """ Pick output file by opening dialog window. """
    now = datetime.now()
    fn = "ducktracker"
    fn += now.strftime("_%Y-%m-%d.txt")
    filename = filedialog.asksaveasfilename(filetypes=[("Text File", "*.txt")],
                                            defaultextension=".txt",
                                            initialfile=fn)

    return filename


def pull_firebase():
    """ Pulls JSON from Firebase. Calls write_out() with JSON object """
    url = "https://ducktracker-d95db.firebaseio.com/.json"
    response = request.urlopen(url)
    data = json.loads(response.read())

    write_out(data, pick_output())


def main():
    """ Uses Tkinter to present a GUI file browser for locating JSON input """
    root = tk.Tk()
    root.title("Ducktracker Data Tool")
    root.resizable(False, False)

    msg = "This tool is provided to download Ducktracker's database " \
          "\n(stored in JSON format) as a human-readable, tab-delimited text file."

    question = tk.Label(root, text=msg)
    question.grid(row=0, column=1, pady=(15, 10), padx=15, columnspan=3)

    button_pull = tk.Button(root, text="Get real time data",
                            command=lambda: [pull_firebase(), root.destroy()])
    button_pull.grid(row=1, column=2, pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
