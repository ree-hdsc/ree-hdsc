import ast
import json
import os
import re
import xml.etree.ElementTree as ET

class ReadTranskribusFiles:
    """Read xml output files of the program Transkribus"""


    def get_value_string(self, fields):
        value_string = fields.pop(0)
        while fields and not re.search("}$", value_string):
            value_string += fields.pop(0)
        return value_string


    def string_to_dict(self, string):
        string = re.sub("^{", "", string)
        string = re.sub(";}$", "", string)
        pairs = string.split(";")
        data = {}
        for pair in pairs:
            pair_data = pair.split(":")
            data[pair_data[0]] = pair_data[1]
        return data


    def process_custom_attrib(self, custom_line):
        fields = custom_line.split()
        data = {}
        while fields:
            key = fields.pop(0)
            if not fields:
                data[key] = {}
            else:
                value_string = self.string_to_dict(self.get_value_string(fields))
                data[key] = value_string
        return data


    def add_length_to_offset(self, metadata_value, text_length):
        for key in metadata_value:
            if key == "offset":
                metadata_value[key] = int(metadata_value[key]) + text_length
        return metadata_value


    def expand_metadata(self, metadata_base, metadata_new, text_length):
        for key in metadata_new:
            if key in metadata_base:
                metadata_base[key].append(self.add_length_to_offset(metadata_new[key], text_length))
            else:
                metadata_base[key] = [self.add_length_to_offset(metadata_new[key], text_length)]


    def process_textline_attrib(self, attribs):
        for attrib in attribs:
            if attrib == "custom":
                return self.process_custom_attrib(attribs[attrib])


    def remove_strikethroughs(self, text_line, custom_dict):
        if "textStyle" not in custom_dict:
            return text_line
        chars = list(text_line)
        for strikethrough in custom_dict["textStyle"]:
            if "strikethrough" in strikethrough:
                start = int(strikethrough["offset"])
                for i in range(start, start + int(strikethrough["length"])):
                    chars[i] = " "
        return "".join(chars)


    def json_string_add_quotes(self, string):
        return re.sub("{ *", "{ '",
                   re.sub(": *", "': '",
                       re.sub("; *", "', '",
                           re.sub("} *'", "} ",
                               re.sub("; *}", "' }", string)))))


    def make_custom_dict(self, text_line_attributes):
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
                custom_dict[custom_key].append(ast.literal_eval(self.json_string_add_quotes(custom_value)))
            else:
                custom_dict[custom_key] = [ast.literal_eval(self.json_string_add_quotes(custom_value))]
        return custom_dict


    def get_text_from_xml(self, root):
        text = ""
        metadata = {}
        for textline in root.findall(".//{*}TextLine"):
            self.expand_metadata(metadata, self.process_textline_attrib(textline.attrib), len(text))
            custom_dict = self.make_custom_dict(textline.attrib)
            for unicode in textline.findall("./{*}TextEquiv/{*}Unicode"):
                if unicode.text != None:
                    text += self.remove_strikethroughs(unicode.text, custom_dict) + "\n"
        return text, metadata


    def convert_to_lists_coords(self, coords):
        pairs = coords.split()
        x_coords = []
        y_coords = []
        for pair in pairs:
            x, y = pair.split(",")
            x_coords.append(int(x))
            y_coords.append(int(y))
        return x_coords, y_coords


    def get_extreme_points_coords(self, coords):
        if coords == "":
            return 0, 0, 0, 0
        x_coords, y_coords = self.convert_to_lists_coords(coords)
        return min(x_coords), max(x_coords), min(y_coords), max(y_coords)


    def get_textregions_from_xml(self, root):
        textregions = []
        for textregion in root.findall(".//{*}TextRegion"):
            for coords in textregion.findall("./{*}Coords"):
                textregions.append(self.get_extreme_points_coords(coords.attrib["points"]))
        return textregions


    def get_text_from_file(self, file_name):
        tree = ET.parse(file_name)
        root = tree.getroot()
        text, metadata = self.get_text_from_xml(root)
        textregions = self.get_textregions_from_xml(root)
        return text, metadata, textregions


    def print_with_color(self, string, color_code=1):
        print(f"\x1b[3{color_code}m{string}\x1b[m", end="")


    def read_files(self, data_dir):
        texts, metadata, textregions = ({}, {}, {})
        for file_name in sorted(os.listdir(data_dir)):
            if re.search("\.xml$", file_name):
                file_id = int(re.sub("\D", "", file_name))
                try:
                    texts[file_id], metadata[file_id], textregions[file_id] = self.get_text_from_file(os.path.join(data_dir, file_name))
                except:
                    self.print_with_color(f"error processing file {file_id}\n")
        return texts, metadata, textregions


    if __name__ == "__main__":
        pass
