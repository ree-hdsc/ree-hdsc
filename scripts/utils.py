import re


def cleanup(text_in):
    """ remove punctuation, successive white space and combine split words """
    text_out = re.sub("\s+", " ", text_in)
    text_out = re.sub("- ", "", text_out)
    return re.sub("[,.]", "", text_out.lower())


def print_with_color(string, color_code=1):
    """ print a text with a color: default red; requires explicit newline """
    print(f"\x1b[3{color_code}m{string}\x1b[m", end="")
