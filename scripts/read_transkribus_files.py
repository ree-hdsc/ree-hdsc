import ast
import json
import os
import re
import xml.etree.ElementTree as ET


def get_value_string(fields):
    value_string = fields.pop(0)
    while fields and not re.search("}$", value_string):
        value_string += fields.pop(0)
    return value_string


def string_to_dict(string):
    string = re.sub("^{", "", string)
    string = re.sub(";}$", "", string)
    pairs = string.split(";")
    data = {}
    for pair in pairs:
        pair_data = pair.split(":")
        data[pair_data[0]] = pair_data[1]
    return data


def process_custom_attrib(custom_line):
    fields = custom_line.split()
    data = {}
    while fields:
        key = fields.pop(0)
        if not fields:
            data[key] = []
        else:
            value_string = string_to_dict(get_value_string(fields))
            if key in data:
                data[key].append(value_string)
            else:
                data[key] = [value_string]
    return data


def add_length_to_offset(metadata_value, text_length):
    for key in metadata_value:
        if key == "offset":
            metadata_value[key] = int(metadata_value[key]) + text_length
    return metadata_value


def expand_metadata(metadata_base, metadata_new, text_length):
    for key in metadata_new:
        if key in metadata_base:
            for value in metadata_new[key]:
                metadata_base[key].append(add_length_to_offset(value, text_length))
        else:
            metadata_base[key] = []
            for value in metadata_new[key]:
                metadata_base[key].append(add_length_to_offset(value, text_length))


def process_textline_attrib(attribs):
    for attrib in attribs:
        if attrib == "custom":
            return process_custom_attrib(attribs[attrib])


def remove_strikethroughs(text_line, custom_dict):
    if "textStyle" not in custom_dict:
        return text_line
    chars = list(text_line)
    for strikethrough in custom_dict["textStyle"]:
        if "strikethrough" in strikethrough:
            start = int(strikethrough["offset"])
            for i in range(start, start + int(strikethrough["length"])):
                chars[i] = " "
    return "".join(chars)


def json_string_add_quotes(string):
    return re.sub("{ *", "{ '",
                re.sub(": *", "': '",
                    re.sub("; *", "', '",
                        re.sub("} *'", "} ",
                            re.sub("; *}", "' }", string)))))


def make_custom_dict(text_line_attributes):
    if "custom" not in text_line_attributes:
        return {}
    custom_tokens = text_line_attributes["custom"].split()
    custom_dict = {}
    while custom_tokens:
        custom_key = custom_tokens.pop(0)
        custom_value = custom_tokens.pop(0)
        while custom_tokens and not re.search("}$", custom_value):
            custom_value += " " + custom_tokens.pop(0)
        if custom_key in custom_dict:
            custom_dict[custom_key].append(ast.literal_eval(json_string_add_quotes(custom_value)))
        else:
            custom_dict[custom_key] = [ast.literal_eval(json_string_add_quotes(custom_value))]
    return custom_dict


def get_text_from_xml(root):
    text = ""
    metadata = {}
    for textline in root.findall(".//{*}TextLine"):
        expand_metadata(metadata, process_textline_attrib(textline.attrib), len(text))
        custom_dict = make_custom_dict(textline.attrib)
        for unicode in textline.findall("./{*}TextEquiv/{*}Unicode"):
            if unicode.text != None:
                text += remove_strikethroughs(unicode.text, custom_dict) + "\n"
    return text, metadata


def convert_to_lists_coords(coords):
    pairs = coords.split()
    x_coords = []
    y_coords = []
    for pair in pairs:
        x, y = pair.split(",")
        x_coords.append(int(x))
        y_coords.append(int(y))
    return x_coords, y_coords


def get_extreme_points_coords(coords):
    if coords == "":
        return 0, 0, 0, 0
    x_coords, y_coords = convert_to_lists_coords(coords)
    return min(x_coords), max(x_coords), min(y_coords), max(y_coords)


def get_textregions_from_xml(root):
    textregions = []
    for textregion in root.findall(".//{*}TextRegion"):
        for coords in textregion.findall("./{*}Coords"):
            textregions.append(get_extreme_points_coords(coords.attrib["points"]))
    return textregions


def get_text_from_file(file_name):
    tree = ET.parse(file_name)
    root = tree.getroot()
    text, metadata = get_text_from_xml(root)
    textregions = get_textregions_from_xml(root)
    return text, metadata, textregions


def print_with_color(string, color_code=1):
    print(f"\x1b[3{color_code}m{string}\x1b[m", end="")


def make_file_id(file_name):
    try:
        year = file_name.split()[1]
        folio_nbr = re.sub("\..*$", "", file_name.split()[-1])
        district = re.sub("(Buiten|distr.|Stad)", "", "".join(file_name.split()[2: -1]))
        if district == "":
            district = "1e"
        return "-".join([year, district, folio_nbr])
    except:
        return file_name


def read_files(data_dir):
    texts, metadata, textregions = ({}, {}, {})
    for file_name in sorted(os.listdir(data_dir)):
        if re.search("\.xml$", file_name):
            file_id = make_file_id(file_name)
            try:
                texts[file_id], metadata[file_id], textregions[file_id] = get_text_from_file(os.path.join(data_dir, file_name))
            except:
                print_with_color(f"error processing file {file_id}\n")
    return texts, metadata, textregions


if __name__ == "__main__":
    pass
