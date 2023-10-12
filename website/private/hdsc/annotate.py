#!/usr/bin/python3

import datetime
import numpy
import os
import pandas as pd
import random
import regex
import sys
from unidecode import unidecode
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET
from flask import Flask, request, render_template


CORPUS_DIR = "data/"
COORDINATES_DIR = CORPUS_DIR + "page/"
TRANSPARENT_BACKGROUND = 255
COVERED_BACKGROUND = 128
DECEASED_NAME_DEFAULT_X_POS = 693
DECEASED_NAME_DEFAULT_Y_POS = 469
DECEASED_NAME_DEFAULT_Y_LINE = 510
MINIMUM_TEXT_AREA = 6000 # about 80% of smallest text field found


def polygon2rectangle(coordinates):
    x_min, x_max, y_min, y_max = (1000000, 0, 1000000, 0)
    for x, y in coordinates:
        if x < x_min: x_min = x
        if x > x_max: x_max = x
        if y < y_min: y_min = y
        if y > y_max: y_max = y
    return x_min, y_min, x_max, y_max


# code based on https://stackoverflow.com/questions/22588074/polygon-crop-clip-using-python-pil

def mark_polygon(image, polygon, covered_background=COVERED_BACKGROUND):
    image_with_transparency = image.convert("RGBA")
    numpy_image = numpy.asarray(image_with_transparency)
    masked_image = Image.new('P', (numpy_image.shape[1], numpy_image.shape[0]), covered_background)
    ImageDraw.Draw(masked_image).polygon(polygon, outline=0, fill=TRANSPARENT_BACKGROUND)
    mask = numpy.array(masked_image)
    masked_numpy_image = numpy.empty(numpy_image.shape, dtype='uint8')
    masked_numpy_image[:,:,:3] = numpy_image[:,:,:3]
    masked_numpy_image[:,:,3] = mask
    return Image.fromarray(masked_numpy_image, "RGBA")


def make_image_file_name(coordinates_file_name):
    if coordinates_file_name == "":
        return ""
    return os.path.join(CORPUS_DIR, regex.sub("xml$", "JPG", os.path.basename(coordinates_file_name)))


def get_coordinates_from_line(line):
    split_line = [ pair.split(",") for pair in line.split() ]
    return [ ( int(x), int(y) ) for x, y in split_line ]


def encloses_point(rectangle, point):
    return(rectangle[0] <= point[0] and rectangle[2] >= point[0] and
           rectangle[1] <= point[1] and rectangle[3] >= point[1])


def find_top_left(polygon):
    top_coordinate = 1000000
    left_coordinate = 1000000
    for pair in polygon[0]:
        if pair[1] < top_coordinate:
            top_coordinate = pair[1]
        if pair[0] < left_coordinate:
            left_coordinate = pair[0]
    return top_coordinate, left_coordinate


def sort_polygons(polygons):
    extended_polygons = []
    for polygon in polygons:
        top_coordinate, left_coordinate = find_top_left(polygon)
        extended_polygons.append([top_coordinate, left_coordinate, polygon])
    return [ extended_polygon[2] for extended_polygon in sorted(extended_polygons, key=lambda ep: (ep[0], ep[1])) ]


def get_text_polygons(coordinates_file_name):
    root = ET.parse(coordinates_file_name).getroot()
    polygons = []
    for text_region in root.findall(".//{*}TextRegion"):
        text_region_polygons = []
        for text_line in text_region.findall("./{*}TextLine"):
            text_region_polygons.append([])
            for coords in text_line.findall("./{*}Coords"):
                text_region_polygons[-1].append(get_coordinates_from_line(coords.attrib["points"]))
        if len(text_region_polygons) > len(polygons):
            polygons = sort_polygons(text_region_polygons)
    return polygons


def get_best_polygon_for_y(polygons, best_y):
    best_distance, best_text_line_id, best_coords_id = (sys.maxsize, -1, -1)
    for text_line_id in range(0, len(polygons)):
        for coords_id in range(0, len(polygons[text_line_id])):
            rectangle = polygon2rectangle(polygons[text_line_id][coords_id])
            distance = abs(best_y - rectangle[1])
            if distance < best_distance and compute_rectangle_area(rectangle) >= MINIMUM_TEXT_AREA:
                best_distance = distance
                best_text_line_id = text_line_id
                best_coords_id = coords_id
    return best_text_line_id, best_coords_id


def get_text_position(polygons, best_position, best_y):
    for text_line_id in range(0, len(polygons)):
        for coords_id in range(0, len(polygons[text_line_id])):
            rectangle = polygon2rectangle(polygons[text_line_id][coords_id])
            if encloses_point(rectangle, best_position) and compute_rectangle_area(rectangle) >= MINIMUM_TEXT_AREA:
                return text_line_id, coords_id
    return get_best_polygon_for_y(polygons, best_y)


def compute_rectangle_area(rectangle):
    x_min, y_min, x_max, y_max = rectangle
    return (x_max - x_min) * (y_max - y_min)


def move_ids(polygons, text_line_id, coords_id, count):
    if count == 0:
        return text_line_id, coords_id
    elif count > 0:
        text_line_id, coords_id = get_next_ids(polygons, text_line_id, coords_id)
        increment = -1
    elif count < 0:
        text_line_id, coords_id = get_previous_ids(polygons, text_line_id, coords_id)
        increment = 1
    else:
        sys.exit("move_ids: cannot happen")
    rectangle = polygon2rectangle(polygons[text_line_id][coords_id])
    if compute_rectangle_area(rectangle) >= MINIMUM_TEXT_AREA:
        return move_ids(polygons, text_line_id, coords_id, count + increment)
    else: # potential infinite loop
        return move_ids(polygons, text_line_id, coords_id, count)


def get_previous_ids(polygons, text_line_id, coords_id):
    if text_line_id == 0 and coords_id == 0:
        return len(polygons) - 1, len(polygons[-1]) - 1
    if coords_id <= 0:
        return text_line_id - 1, len(polygons[text_line_id - 1]) - 1
    else:
        return text_line_id, coords_id - 1


def get_next_ids(polygons, text_line_id, coords_id):
    if text_line_id == len(polygons) - 1 and coords_id == len(polygons[-1]) - 1:
        return 0, 0
    if coords_id >= len(polygons[text_line_id]) - 1:
        return text_line_id + 1, 0
    else:
        return text_line_id, coords_id + 1


def read_processed_files():
    return pd.read_csv("etc/logfile")


def select_next_file():
    coordinates_file_list = sorted(os.listdir(COORDINATES_DIR))
    processed_files = list(read_processed_files().iloc[:,0])
    unprocessed_files = [ file_name for file_name in coordinates_file_list if file_name not in processed_files ]
    if len(unprocessed_files) == 0:
        return ""
    while True:
        coordinates_file_name = unprocessed_files[random.randint(0, len(unprocessed_files) - 1)]
        deceased_name = get_deceased_name(coordinates_file_name)
        if regex.search("(unknown|levenloos|levensloos)", deceased_name, regex.IGNORECASE) or len(get_text_polygons(os.path.join(COORDINATES_DIR, coordinates_file_name))) == 0:
            update_logfile(os.path.basename(coordinates_file_name), "skip", 0, 0, deceased_name, "0.0.0.0")
        else:
            break
    return os.path.join(COORDINATES_DIR, coordinates_file_name)


def first_char_to_upper(name):
    chars = list(name)
    chars[0] = chars[0].upper()
    return "".join(chars)


def fix_lower_and_upper_case(name_parts, prefix_words):
    for i in range(0, len(name_parts)):
        if regex.search(r"^[A-Z,]+$", name_parts[i]):
            name_parts[i] = name_parts[i].lower()
        if regex.search(r"^[a-z,]+$", name_parts[i]) and name_parts[i] not in prefix_words:
            name_parts[i] = first_char_to_upper(name_parts[i])
    return name_parts


def move_prefix_words(name_parts, prefix_words):
    last_i = len(name_parts)
    while last_i > 0 and name_parts[last_i - 1].lower() in prefix_words:
        last_i -= 1
    if last_i == len(name_parts) - 1 and name_parts[last_i].lower() == "da":
        for i in range(last_i - 1, 0, -1):
            if name_parts[i].lower() == "costa":
                name_parts = name_parts[:i] + name_parts[last_i:] + name_parts[i:last_i-1] + [regex.sub(",$", "", name_parts[last_i-1])]
                last_i = len(name_parts)
                break
    if last_i < len(name_parts) and last_i > 0:
        name_parts = name_parts[:last_i-1] + name_parts[last_i:] + [regex.sub(",$", "", name_parts[last_i-1])]
    return name_parts


def normalize_name(name):
    prefix_words = [ "da", "de", "den", "der", "la", "le", "van" ]
    name_parts = unidecode(name).split()
    name_parts = fix_lower_and_upper_case(name_parts, prefix_words)
    name_parts = move_prefix_words(name_parts, prefix_words)
    return " ".join(name_parts)


def get_deceased_name(coordinates_file_name):
    short_file_name = os.path.splitext(os.path.basename(coordinates_file_name))[0]
    data = pd.read_csv(CORPUS_DIR + "Overlijdensmerged.csv", low_memory=False)
    data_selection = data.loc[data["Scans"] == short_file_name]
    if len(data_selection) == 0:
        return f"unknown name"
    else:
        first_names = data_selection.iloc[0]["Voornamen"]
        last_name = data_selection.iloc[0]["Achternaam"]
        if type(first_names) != str or first_names == "":
            if type(last_name) != str or last_name == "":
                return "unknown name"
            else:
                return normalize_name(last_name)
        elif type(last_name) != str or last_name == "":
            return normalize_name(first_names)
        else:
            return normalize_name(f"{first_names} {last_name}")


def remove_last_entry():
    lines = []
    logfile = open("etc/logfile", "r")
    for line in logfile:
        lines.append(line.strip())
    logfile.close()
    lines.pop(-1)
    logfile = open("etc/logfile", "w")
    for line in lines:
        print(line, file=logfile)
    logfile.close()


def resize_image(image, resize_factor):
    width, height = image.size
    return image.resize((int(width/resize_factor), int(height/resize_factor)))


def resize_polygon(polygon, factor):
    return [ tuple([int(value/factor) for value in coordinates]) for coordinates in polygon ]


def update_logfile(file_name, action, text_line_id, coords_id, deceased_name, ip_addr):
    logfile = open("etc/logfile", "a")
    print(f"{file_name},{action},{text_line_id},{coords_id},\"{deceased_name}\",{ip_addr},{datetime.date.today()}", file=logfile)
    logfile.close()


app = Flask(__name__)


def determine_file_names(request, ip_addr):
    if "go_back" in request.form:
        coordinates_file_name = os.path.join(COORDINATES_DIR, request.form["previous_file_name"])
        previous_file_name = request.form["file_name"]
    elif "move_frame" in request.form:
        coordinates_file_name = os.path.join(COORDINATES_DIR, request.form["file_name"])
        previous_file_name = request.form["previous_file_name"]
    elif "annotate" in request.form:
        update_logfile(request.form["file_name"], request.form["annotate"], request.form["text_line_id"], request.form["coords_id"], request.form["deceased_name"], ip_addr)
        coordinates_file_name = select_next_file()
        previous_file_name = request.form["file_name"]
    elif request.args.get("file_name") != None:
        coordinates_file_name = os.path.join(COORDINATES_DIR, request.args.get("file_name"))
        previous_file_name = ""
    else:
        coordinates_file_name = select_next_file()
        previous_file_name = ""
    return coordinates_file_name, previous_file_name


def determine_polygon(polygons, request):
    if "move_frame" not in request.form:
        text_line_id, coords_id = get_text_position(polygons, [DECEASED_NAME_DEFAULT_X_POS, DECEASED_NAME_DEFAULT_Y_POS], DECEASED_NAME_DEFAULT_Y_LINE)
    else:
        text_line_id = int(request.form["text_line_id"])
        coords_id = int(request.form["coords_id"])
        if request.form["move_frame"] == "minus5":
            text_line_id, coords_id = move_ids(polygons, text_line_id, coords_id, -5)
        elif request.form["move_frame"] == "prev":
            text_line_id, coords_id = move_ids(polygons, text_line_id, coords_id, -1)
        elif request.form["move_frame"] == "next":
            text_line_id, coords_id = move_ids(polygons, text_line_id, coords_id, 1)
        elif request.form["move_frame"] == "plus5":
            text_line_id, coords_id = move_ids(polygons, text_line_id, coords_id, 5)
    return text_line_id, coords_id


def prepare_image(image_file_name, polygon, ip_addr):
    img_dir = f"../../htdocs/hdsc/{ip_addr}/"
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    resize_factor = 4
    image = resize_image(Image.open(image_file_name), resize_factor)
    marked_image = mark_polygon(image, resize_polygon(polygon, resize_factor))
    marked_image.save(f"{img_dir}/image.png", optimize=True, quality=1)


@app.route("/", methods=['GET', 'POST'])
def annotate():
    ip_addr = request.remote_addr
    coordinates_file_name, previous_file_name = determine_file_names(request, ip_addr)
    if coordinates_file_name == "":
        return render_template("finished.html")
    image_file_name = make_image_file_name(coordinates_file_name)
    deceased_name = get_deceased_name(coordinates_file_name)
    polygons = get_text_polygons(coordinates_file_name)
    text_line_id, coords_id = determine_polygon(polygons, request)
    prepare_image(image_file_name, polygons[text_line_id][coords_id], ip_addr)
    return render_template("index.html",
                           text_line_id=text_line_id,
                           coords_id=coords_id,
                           file_name=os.path.basename(coordinates_file_name),
                           previous_file_name=previous_file_name,
                           deceased_name=deceased_name,
                           ip_addr=ip_addr,
                           nbr_of_processed_files=len(read_processed_files()),
                           nbr_of_files=len(os.listdir(COORDINATES_DIR)))


@app.route("/stats", methods=['GET', 'POST'])
def stats():
    data = read_processed_files()
    labels = {}
    file_names = {}
    nbr_of_saved = 0
    nbr_of_skipped = 0
    date_counts = {}
    total_files = len(os.listdir(COORDINATES_DIR))
    for row_id, row in data.iterrows():
        file_name = row[0]
        label = row[1]
        date = int(regex.sub("-", "", row[6]))
        year = int(file_name.split()[1])
        if file_name in file_names:
            labels[year][file_names[file_name]] -= 1
        if year not in labels:
            labels[year] = {}
        if label not in labels[year]:
            labels[year]["save"] = 0
            labels[year]["skip"] = 0
        labels[year][label] += 1
        if label == "save":
            nbr_of_saved += 1
        elif label == "skip":
            nbr_of_skipped += 1
        file_names[file_name] = label
        if date not in date_counts:
            date_counts[date] = 0
        date_counts[date] += 1
    last_date = ""
    for date in sorted(list(date_counts.keys())):
        if last_date != "":
            date_counts[date] += date_counts[last_date]
        last_date = date
    return render_template("stats.html", 
                           nbr_of_saved=nbr_of_saved, 
                           nbr_of_skipped=nbr_of_skipped, 
                           labels=sorted(list(labels.keys()))[:20], 
                           counts_saved=[labels[year]["save"] for year in sorted(list(labels.keys()))][:20],
                           counts_skipped=[labels[year]["skip"] for year in sorted(list(labels.keys()))][:20],
                           x_values=sorted(list(date_counts.keys())),
                           y_values=[date_counts[date] for date in sorted(list(date_counts.keys()))],
                           total_files=total_files)

