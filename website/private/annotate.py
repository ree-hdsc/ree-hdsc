#!/usr/bin/env python3

import numpy
import os
import sys
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET
sys.path.append(os.getcwd() + '/../ree-hdsc')
from scripts import read_transkribus_files
from IPython.display import clear_output
from flask import Flask, request


CORPUS_DIR = "../data/Overlijden/"
COORDINATES_DIR = CORPUS_DIR + "x-samples/three-columns-100/corrected/"

TRANSPARENT_BACKGROUND = 255
COVERED_BACKGROUND = 128

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
    return os.path.join(CORPUS_DIR, year_dir, district_dir, regex.sub("xml$", "JPG", coordinates_file_name))


def get_coordinates_from_line(line):
    split_line = [ pair.split(",") for pair in line.split() ]
    return [ ( int(x), int(y) ) for x, y in split_line ]


def encloses_point(rectangle, point):
    return(rectangle[0] <= point[0] and rectangle[2] >= point[0] and
           rectangle[1] <= point[1] and rectangle[3] >= point[1])


app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def hello_world():
    text = "<p>Hello, World!</p>"
    text += '<form method="post"><button type="submit" name="name" value="Download">Download</button><button type="submit" name="name" value="Watch">Watch</button></form>'
    if "name" in request.form:
        text += str(request.form["name"])
    return text

