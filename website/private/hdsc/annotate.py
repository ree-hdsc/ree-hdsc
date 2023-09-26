#!/usr/bin/python3

import numpy
import os
import pandas as pd
import random
import regex
import sys
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET
from flask import Flask, request


CORPUS_DIR = "data/"
COORDINATES_DIR = CORPUS_DIR + "page/"

TRANSPARENT_BACKGROUND = 255
COVERED_BACKGROUND = 128
DECEASED_NAME_X_POS = 600
DECEASED_NAME_Y_POS = 460


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
    file_name_parts = coordinates_file_name.split()
    year_dir = " ".join(file_name_parts[:2])
    district_dir = regex.sub("\.$", "", " ".join(file_name_parts[:-1]))
    return os.path.join(CORPUS_DIR, regex.sub("xml$", "JPG", coordinates_file_name))


def get_coordinates_from_line(line):
    split_line = [ pair.split(",") for pair in line.split() ]
    return [ ( int(x), int(y) ) for x, y in split_line ]


def encloses_point(rectangle, point):
    return(rectangle[0] <= point[0] and rectangle[2] >= point[0] and
           rectangle[1] <= point[1] and rectangle[3] >= point[1])


def get_text_polygons(coordinates_file_name):
    root = ET.parse(coordinates_file_name).getroot()
    polygons = []
    for text_line in root.findall(".//{*}TextLine"):
        polygons.append([])
        for coords in text_line.findall("./{*}Coords"):
            polygons[-1].append(get_coordinates_from_line(coords.attrib["points"]))
    return polygons


def get_text_position(polygons, position):
    for text_line_id in range(0, len(polygons)):
        for coords_id in range(0, len(polygons[text_line_id])):
            rectangle = polygon2rectangle(polygons[text_line_id][coords_id])
            if encloses_point(rectangle, position):
                return text_line_id, coords_id
    return -1, -1


def get_previous_ids(polygons, text_line_id, coords_id):
    if coords_id <= 0:
        if text_line_id <= 0:
            return -1, -1
        else:
            return text_line_id - 1, len(polygons[text_line_id - 1]) - 1
    else:
        return text_line_id, coords_id - 1


def get_next_ids(polygons, text_line_id, coords_id):
    if coords_id >= len(polygons[text_line_id]) - 1:
        if text_line_id >= len(polygons) - 1:
            return -1, -1
        else:
            return text_line_id + 1, 0
    else:
        return text_line_id, coords_id + 1


def read_processed_files():
    data = pd.read_csv("etc/logfile")
    return list(data.iloc[:,0])


def select_next_file(coordinates_file_list):
    processed_files = read_processed_files()
    unprocessed_files = [ file_name for file_name in coordinates_file_list if file_name not in processed_files ]
    if len(unprocessed_files) == 0:
        return "", ""
    coordinates_file_name = unprocessed_files[random.randint(0, len(unprocessed_files) - 1)]
    image_file_name = make_image_file_name(coordinates_file_name)
    return os.path.join(COORDINATES_DIR, coordinates_file_name), image_file_name


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
                return ""
            else:
                return last_name
        elif type(last_name) != str or last_name == "":
            return first_names
        else:
            return f"{first_names} {last_name}"


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


app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def check_data():
    form_processed = False
    ip_addr = request.remote_addr
    if "action" in request.form:
        action = request.form["action"]
        text_line_id = request.form["text_line_id"]
        coords_id = request.form["coords_id"]
        file_name = request.form["file_name"]
        deceased_name = request.form["deceased_name"]
        logfile = open("etc/logfile", "a")
        print(f"{file_name},{action},{text_line_id},{coords_id},\"{deceased_name}\",{ip_addr}", file=logfile)
        logfile.close()
        form_processed = True
    if "file_name" in request.form:
        previous_file_name = request.form["file_name"]
    else:
        previous_file_name = ""
    #if "deceased_name_x_pos" in request.form:
    #    deceased_name_x_pos = int(request.form["deceased_name_x_pos"])
    #    deceased_name_y_pos = int(request.form["deceased_name_y_pos"])
    #else:
    deceased_name_x_pos = DECEASED_NAME_X_POS
    deceased_name_y_pos = DECEASED_NAME_Y_POS
    coordinates_file_list = sorted(os.listdir(COORDINATES_DIR))
    coordinates_file_name, image_file_name = select_next_file(coordinates_file_list)
    deceased_name = get_deceased_name(coordinates_file_name)
    if coordinates_file_name == "":
        return "Done!"
    polygons = get_text_polygons(coordinates_file_name)
    if not form_processed and "text_line_id" in request.form and "coords_id" in request.form:
        text_line_id = int(request.form["text_line_id"])
        coords_id = int(request.form["coords_id"])
    else:
        text_line_id, coords_id = get_text_position(polygons, [deceased_name_x_pos, deceased_name_y_pos])
    if text_line_id >= 0:
        if not form_processed:
            if "name" in request.form and str(request.form["name"]) == "prev":
                text_line_id, coords_id = get_previous_ids(polygons, text_line_id, coords_id)
                coordinates_file_name = request.form["file_name"]
                image_file_name = make_image_file_name(coordinates_file_name)
                coordinates_file_name = os.path.join(COORDINATES_DIR, coordinates_file_name)
                deceased_name = get_deceased_name(coordinates_file_name)
                polygons = get_text_polygons(coordinates_file_name)
            if "name" in request.form and str(request.form["name"]) == "next":
                text_line_id, coords_id = get_next_ids(polygons, text_line_id, coords_id)
                coordinates_file_name = request.form["file_name"]
                image_file_name = make_image_file_name(coordinates_file_name)
                coordinates_file_name = os.path.join(COORDINATES_DIR, coordinates_file_name)
                deceased_name = get_deceased_name(coordinates_file_name)
                polygons = get_text_polygons(coordinates_file_name)
            if "back" in request.form:
                coordinates_file_name = request.form["previous_file_name"]
                image_file_name = make_image_file_name(coordinates_file_name)
                coordinates_file_name = os.path.join(COORDINATES_DIR, coordinates_file_name)
                deceased_name = get_deceased_name(coordinates_file_name)
                polygons = get_text_polygons(coordinates_file_name)
        # to be saved: text_line_list[text_line_id].attrib["id"] ?
        polygon = polygons[text_line_id][coords_id]
    else:
        text_line_id = int(len(polygons)/2)
        coords_id = 0
        polygon = polygons[text_line_id][coords_id]
    rectangle = polygon2rectangle(polygon)
    deceased_name_x_pos = int((rectangle[0] + rectangle[2])/2)
    deceased_name_y_pos = int((rectangle[1] + rectangle[3])/2)
    image = Image.open(image_file_name)
    marked_image = mark_polygon(image, polygon)
    img_dir = f"../../htdocs/hdsc/{ip_addr}/"
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    marked_image.save(f"{img_dir}/image.png")
    web_text = f"""<html>
 <head><title>annotate></title></head>
 <body>
  <form method="post">
   <input type="hidden" name="text_line_id" value="{text_line_id}">
   <input type="hidden" name="coords_id" value="{coords_id}">
   <input type="hidden" name="file_name" value="{os.path.basename(coordinates_file_name)}">
   <input type="hidden" name="previous_file_name" value="{previous_file_name}">
   <input type="hidden" name="deceased_name" value="{deceased_name}">
   <input type="hidden" name="deceased_name_x_pos" value="{deceased_name_x_pos}">
   <input type="hidden" name="deceased_name_y_pos" value="{deceased_name_y_pos}">
   <button type="submit" name="back" value="back">back</button> (zie instructies onderaan)<br>
   <button type="submit" name="name" value="prev">previous</button>
   <button type="submit" name="name" value="next">next</button><br>
   <button type="submit" name="action" value="skip">skip</button>
   <button type="submit" name="action" value="save">save</button>
  </form>
  <p>{os.path.basename(coordinates_file_name)}:</p>
  <table>
   <tr>
    <td>{deceased_name}<br><br><br><br><br>&nbsp;</td>
    <td><img src="/hdsc/{ip_addr}/image.png" width="600"> {len(read_processed_files())}/{len(coordinates_file_list)}</td>
    </td>
   </tr>
  </table>
  <p>
   <strong>Instructies</strong>
   <br>Klik op "save" als de naam links hetzelfde is als de opgelichte naam in het document
   <br>Klik op "previous" of "next" om het opgelichte deel te verschuiven
   <br>Klik op "skip":
  </p>
  <ol>
   <li> als de naam links anders is dan de naam in het document
    <br> (ook als "van" of "de" op de verkeerde plaats staat)
   <li> als links staat "unknown name" of "levenloos"
   <li> als het document geen naam bevat
   <li> als het opgelichte deel meer of minder tekst bevat dan de naam links
   <li> bij twijfel: altijd op "skip" drukken
  </ol>
  <p>
   Als je een fout maakt dan kan je met "back" terug naar het vorige document
   <br>Deze tool is niet geschikt voor tegelijkertijd gebruik door meerdere mensen
   <br>Stuur vragen en opmerkingen naar e.tjongkimsang@esciencecenter.nl
  </p>
 </body>
</html>
"""
    return web_text

