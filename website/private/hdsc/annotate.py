#!/usr/bin/python3

import numpy
import os
import pandas as pd
import random
import regex
import sys
from unidecode import unidecode
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
    return pd.read_csv("etc/logfile")


def select_next_file(coordinates_file_list):
    processed_files = list(read_processed_files().iloc[:,0])
    unprocessed_files = [ file_name for file_name in coordinates_file_list if file_name not in processed_files ]
    if len(unprocessed_files) == 0:
        return "", ""
    while True:
        coordinates_file_name = unprocessed_files[random.randint(0, len(unprocessed_files) - 1)]
        image_file_name = make_image_file_name(coordinates_file_name)
        deceased_name = get_deceased_name(coordinates_file_name)
        if regex.search("(unknown|levenloos)", deceased_name, regex.IGNORECASE):
            update_logfile(os.path.basename(coordinates_file_name), "skip", 0, 0, deceased_name, "0.0.0.0")
        else:
            break
    return os.path.join(COORDINATES_DIR, coordinates_file_name), image_file_name, deceased_name


def first_char_to_upper(name):
    chars = list(name)
    chars[0] = chars[0].upper()
    return "".join(chars)


def normalize_name(name):
    stop_words = [ "de", "der", "van" ]
    name_parts = unidecode(name).split()
    for i in range(0, len(name_parts)):
        if regex.search(r"^[A-Z,]+$", name_parts[i]):
            name_parts[i] = name_parts[i].lower()
        if regex.search(r"^[a-z,]+$", name_parts[i]) and name_parts[i] not in stop_words:
            name_parts[i] = first_char_to_upper(name_parts[i])
    last_i = len(name_parts)
    while last_i > 0 and name_parts[last_i - 1] in stop_words:
        last_i -= 1
    if last_i < len(name_parts) and last_i > 0:
        name_parts = name_parts[:last_i-1] + name_parts[last_i:] + [regex.sub(",$", "", name_parts[last_i-1])]
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


def resize_polygon(polygon):
    return [ tuple([int(value/2) for value in coordinates]) for coordinates in polygon ]


def update_logfile(file_name, action, text_line_id, coords_id, deceased_name, ip_addr):
    logfile = open("etc/logfile", "a")
    print(f"{file_name},{action},{text_line_id},{coords_id},\"{deceased_name}\",{ip_addr}", file=logfile)
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
        update_logfile(file_name, action, text_line_id, coords_id, deceased_name, ip_addr)
        form_processed = True
    if "file_name" in request.form:
        previous_file_name = request.form["file_name"]
    else:
        previous_file_name = ""
    deceased_name_x_pos = DECEASED_NAME_X_POS
    deceased_name_y_pos = DECEASED_NAME_Y_POS
    coordinates_file_list = sorted(os.listdir(COORDINATES_DIR))
    coordinates_file_name, image_file_name, deceased_name = select_next_file(coordinates_file_list)
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
        polygon = polygons[text_line_id][coords_id]
    else:
        text_line_id = int(len(polygons)/2)
        coords_id = 0
        polygon = polygons[text_line_id][coords_id]
    rectangle = polygon2rectangle(polygon)
    deceased_name_x_pos = int((rectangle[0] + rectangle[2])/2)
    deceased_name_y_pos = int((rectangle[1] + rectangle[3])/2)
    image = Image.open(image_file_name)
    width, height = image.size
    image = image.resize((int(width/2), int(height/2)))
    marked_image = mark_polygon(image, resize_polygon(polygon))
    img_dir = f"../../htdocs/hdsc/{ip_addr}/"
    if not os.path.isdir(img_dir):
        os.mkdir(img_dir)
    marked_image.save(f"{img_dir}/image.png", optimize=True, quality=1)
    web_text = f"""<html>
 <head><title>annotate</title></head>
 <body>
  <p>
   <a href="/cgi-bin/hdsc/">annotate</a> | <a href="/cgi-bin/hdsc/stats">stats</a>
  </p>
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
   <br>Stuur vragen en opmerkingen naar e.tjongkimsang@esciencecenter.nl
  </p>
 </body>
</html>
"""
    return web_text


@app.route("/stats", methods=['GET', 'POST'])
def stats():
    data = read_processed_files()
    labels = {}
    file_names = {}
    nbr_of_saved = 0
    nbr_of_skipped = 0
    for row_id, row in data.iterrows():
        file_name = row[0]
        label = row[1]
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
    return """
<html>
<head>
<title>number of saved data per year</title>
</head>
<body>
<style>
  #chart-wrapper {
    display: inline-block;
    position: relative;
    width: 25%;
  }
</style>
<p>
 <a href="/cgi-bin/hdsc/">annotate</a> | <a href="/cgi-bin/hdsc/stats">stats</a>
</p>
<h3>number of saved data per year</h3>
<p>
""" + f"""
Number of saved files: {nbr_of_saved} ({int(0.5 + 100 * nbr_of_saved/(nbr_of_saved + nbr_of_skipped))}%)
<br>Number of skipped files: {nbr_of_skipped} ({int(0.5 + 100 * nbr_of_skipped/(nbr_of_saved + nbr_of_skipped))}%)
""" + """

<div id="chart-wrapper">
<canvas id="myChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
  const ctx = document.getElementById('myChart');

  new Chart(ctx, {
    type: 'bar',
    data: {
""" + f"""
      labels: {list(labels.keys())[:20]},
      datasets: [{{
        label: '# of saved data',
        data: {[labels[year]["save"] for year in labels][:20]},
        borderWidth: 1
      }},
      {{
        label: '# of skipped data',
        data: {[labels[year]["skip"] for year in labels][:20]},
        borderWidth: 1
      }}]
""" + """
    },
    options: {
      scales: {
        x: {
          stacked: true
        },
        y: {
          beginAtZero: true,
          stacked: true
        }
      }
    }
  });
</script>

</body>
</html>
"""

