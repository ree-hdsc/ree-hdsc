import re
from spacy import displacy


def cleanup(text_in):
    """ remove punctuation, successive white space and combine split words """
    text_out = re.sub("\s+", " ", text_in)
    text_out = re.sub("- ", "", text_out)
    return re.sub("[,.]", "", text_out.lower())


def print_with_color(string, color_code=1):
    """ print a text with a color: default red; requires explicit newline """
    print(f"\x1b[3{color_code}m{string}\x1b[m", end="")


def find_text_patterns(query, text):
    """ find a text pattern in text """
    positions = []
    pattern = re.compile(query.lower())
    for m in pattern.finditer(text.lower()):
        positions.append({"start": m.start(), "end": m.end()})
    return positions


def render_text(text, entities):
    displacy.render({ "text": re.sub("\\n", " ", text),
                      "ents": entities },
                    options = { "colors": { "fuzzy_match": "yellow"} }, 
                    style = "ent", 
                    manual = True)
