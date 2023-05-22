import re
import sys
from . import utils


ordinals = { "eersten": 1, "tweeden": 2, "derden": 3, "vierden": 4, "vijfden": 5,
             "zesden": 6, "zevenden": 7, "achtsten": 8, "negenden": 9, "tienden": 10,
             "elfden": 11, "twaalfden": 12, "dertienden": 13, "veertienden": 14, "vijftienden": 15,
             "zestienden": 16, "zeventienden": 17, "achttienden": 18, "negentienden": 19, "twintigsten": 20,
             "eenentwintigsten": 21, "tweeentwintigsten": 22, "drieentwintigsten": 23, "vierentwintigsten": 24, "vijfentwintigsten": 25,
             "zesentwintigsten": 26, "zevenentwintigsten": 27, "achtentwintigsten": 28, "negenentwintigsten": 29, "dertigsten": 30,
             "eenendertigsten": 31,
            }


cardinals = { "een": 1, "twee": 2, "drie": 3, "vier": 4,
              "vijf": 5, "zes": 6, "zeven": 7, "acht": 8, "negen": 9,
              "tien": 10, "elf": 11, "twaalf": 12, "dertien": 13, "veertien": 14, "vijftien": 15, 
              "zestien": 16, "zeventien": 17, "achttien":18, "negentien": 19,
              "twintig": 20, "eenentwintig": 21, "tweeentwintig": 22, "drieentwintig": 23, "vierentwintig": 24, 
              "vijfentwintig": 25, "zesentwintig": 26, "zevenentwintig": 27, "achtentwintig": 28, "negenentwintig": 29,
              "dertig": 30, "eenendertig": 31, "tweeendertig": 32, "drieendertig": 33, "vierendertig": 34, 
              "vijfendertig": 35, "zesendertig": 36, "zevenendertig": 37, "achtendertig": 38, "negenendertig": 39,
              "veertig": 40, "eenenveertig": 41, "tweeenveertig": 42, "drieenveertig": 34, "vierenveertig": 44, 
              "vijfenveertig": 45, "zesenveertig": 46, "zevenenveertig": 47, "achtenveertig": 48, "negenenveertig": 49,
              "vijftig": 50, "eenenvijftig": 51, "tweeenvijftig": 52, "drieenvijftig": 53, "vierenvijftig": 54, 
              "vijfenvijftig": 55, "zesenvijftig": 56, "zevenenvijftig": 57, "achtenvijftig": 58, "negenenvijftig": 59,
              "zestig": 60, "eenenzestig": 61, "tweeenzestig": 62, "drieenzestig": 63, "vierenzestig": 64, 
              "vijfenzestig": 65, "zesenzestig": 66, "zevenenzestig": 67, "achtenzestig": 68, "negenenzestig": 69,
              "zeventig": 70, "eenenzeventig": 71, "tweeenzeventig": 72, "drieenzeventig": 73, "vierenzeventig": 74, 
              "vijfenzeventig": 75, "zesenzeventig": 76, "zevenenzeventig": 77, "achtenzeventig": 78, "negenenzeventig": 79,
              "tachtig": 80, "eenentachtig": 81, "tweeentachtig": 82, "drieentachtig": 83, "vierentachtig": 84, 
              "vijfentachtig": 85, "zesentachtig": 86, "zevenentachtig": 87, "achtentachtig": 88, "negenentachtig": 89,
              "negentig": 90, "eenennegentig": 91, "tweeennegentig": 92, "drieennegentig": 93, "vierennegentig": 94, 
              "vijfennegentig": 95, "zesennegentig": 96, "zevenennegentig": 97, "achtennegentig": 98, "negenennegentig": 99,
              "1800": 1800, "1900": 1900
            }


others = { "en": 0, "honderd": 100, "duizend": 1000, }


date_months = { '': 0, "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
                "juli": 7, "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
                "een": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7, "acht": 8, "negen": 9, "tien": 10, "elf": 11, "twaalf": 12,
                "juny": 6, "july": 7, "october": 10, "ovember": 11, "cember": 12 }


MONTH_TABLE = { "januari": "01", "februari": "02", "maart": "03", "april": "04", "mei": "05", "juni": "06",
                "juli": "07", "augustus": "08", "september": "09", "oktober": "10", "november": "11", "december": "12",
                 "een": "01", "twee": "02", "drie": "03", "vier": "04", "vijf": "05", "zes": "06", "zeven": "07", "acht": "08", "negen": "09", "tien": "10", "elf": "11", "twaalf": "12",
                "juny": "06", "july": "07", "october": "10", "ovember": 11, "cember": 12 }


def get_day_from_date(date):
    return date[0]


def get_month_from_date(date):
    return date[1]


def get_year_from_date(date):
    return date[2]


def get_next_token(position, text):
    """ returrn the first token of the text from the current position, with its final position """
    while position < len(text) - 1 and re.search("\s", text[position]):
        position += 1
    token = ""
    while position < len(text) - 1 and not re.search("\s", text[position]):
        token += text[position]
        position += 1
    return token, position


def get_date_day(position, text):
    """ return the number that starts the text """
    return number_parser(text[position:])


def get_date_month(position, text):
    """ return month that starts the text """
    month = ""
    next_token, end_position = get_next_token(position, text)
    if utils.cleanup(next_token) in date_months.keys():
        month = next_token
    else:
        next_next_token, next_end_position = get_next_token(end_position, text)
        next_token = re.sub("-$", "", next_token)
        next_token += next_next_token
        if utils.cleanup(next_token) in date_months.keys():
            month = next_token
            end_position = next_end_position
    if month:
        return month, end_position - position
    else:
        return month, 0


def get_date_year(position, text):
    """ return number that starts the text, possibly prepended with 'des' """
    year = ""
    next_token, next_position = get_next_token(position, text)
    if next_token.lower() != "des":
        return number_parser(text[position:])
    next_token, next_position = get_next_token(next_position, text)
    return number_parser(text[next_position:])


def longest_number_match(text):
    """ find the longest initial string in the text that is a dictionary number """
    longest_match = ""
    longest_match_length = 0
    text_index = 0
    while text_index < len(text) and re.search("\s", text[text_index]):
        text_index += 1
    for i in range(text_index, text_index + 30):
        phrase = utils.cleanup(text[text_index: i])
        if phrase in cardinals.keys() or phrase in ordinals.keys() or phrase in others.keys():
            longest_match = phrase
            longest_match_length = int(i)
        elif phrase + "n" in ordinals.keys():
            longest_match = phrase + "n"
            longest_match_length = int(i)
        else:
            phrase = re.sub("[^a-zA-Z]", "", phrase)
            if phrase in cardinals.keys() or phrase in ordinals.keys() or phrase in others.keys():
                longest_match = phrase
                longest_match_length = int(i)
            elif phrase + "n" in ordinals.keys():
                longest_match = phrase + "n"
                longest_match_length = int(i)
    return longest_match, longest_match_length


def split_off_hundreds_thousands(tokens):
    """ in a token list, make honderd (hundred) and duizend (thousand) separate tokens """
    if re.search(".(honderd|duizend)", tokens[0].lower()):
        tokens.insert(0, re.sub("(honderd|duizend).*", "", tokens[0].lower()))
        tokens[1] = re.sub(".*(honderd|duizend)", "\\1", tokens[1].lower())


def number_parser(text):
    """ identify the number starting the text, return it with its length """
    if not text:
        return 0, 0
    first_number, first_offset = longest_number_match(text)
    second_number, second_offset = longest_number_match(text[first_offset:])
    if utils.cleanup(first_number) == "en":
        number, offset = number_parser(text[first_offset:])
        return number, offset + first_offset
    if utils.cleanup(first_number) in cardinals:
        if utils.cleanup(second_number) == "":
            return cardinals[utils.cleanup(first_number)], first_offset
        elif utils.cleanup(second_number) == "honderd":
            number, offset = number_parser(text[first_offset + second_offset:])
            return 100 * cardinals[utils.cleanup(first_number)] + number, first_offset + second_offset + offset
        elif utils.cleanup(second_number) == "duizend":
            number, offset = number_parser(text[first_offset + second_offset:])
            return 1000 * cardinals[utils.cleanup(first_number)] + number, first_offset + second_offset + offset
        else:
            number, offset = number_parser(text[first_offset:])
            return cardinals[utils.cleanup(first_number)] + number, first_offset + offset
    if utils.cleanup(first_number) in ordinals:
        return ordinals[utils.cleanup(first_number)], first_offset
    return 0, 0


def get_dates(text, pattern):
    """ get dates from a text using the provided text pattern """
    dates = []
    day = ""
    positions = utils.find_text_patterns(pattern, text)
    for position in positions:
        day, token_length_day = get_date_day(position["end"], text)
        month, token_length_month = get_date_month(position["end"] + token_length_day, text)
        year, token_length_year = get_date_year(position["end"] + token_length_day + token_length_month, text)
        dates.append((day,month,year))
    return summarize_dates(dates)


def complete_date(date):
    """ test if a date contains a day, a month and a year """
    return get_day_from_date(date) != 0 and get_month_from_date(date) != "" and get_year_from_date(date) != 0


def contains_complete_date(dates):
    """ test if a date list contains a complete date: day, month, year """
    if not dates:
        return False
    elif complete_date(dates[0]):
        return True
    else:
        return contains_complete_date(dates[1:])


def summarize_dates(dates_in):
    """ remove incomplete dates from date list if it contains complete dates """
    keep_only_complete_dates = contains_complete_date(dates_in)
    dates_out = []
    for date in dates_in:
        (day, month, year) = date
        if complete_date(date):
            dates_out.append(date)
        elif not keep_only_complete_dates and (day != 0 or month != "" or year != 0):
            dates_out.append(date)
    return dates_out


def date_to_numeric(date_in):
    """ convert a date of format '1 January 1900' to the format '01-01-1900' """
    try:
        day_in, month_in, year_in = date_in.split()
        day_out = str(day_in).zfill(2)
        month_out = MONTH_TABLE[month_in.lower()]
        return "-".join([day_out, month_out, year_in])
    except:
        return date_in


def print_dates(text_id, dates, date_of_death_gold, note=""):
    """ show the results of the date analysis (to be updated) """
    summarized_dates = summarize_dates(dates)
    correct_death_date_found = False
    if not summarized_dates:
        utils.print_with_color(f"Text {text_id}: (no dates found)\n")
    for date in summarize_dates(dates):
        (day, month, year) = date
        try:
            gold_date = date_of_death_gold[text_id][0]
        except:
            gold_date = "***"
        try:
            print(f"Text {text_id}: {day} {month} {year} ({ordinals[utils.cleanup(day)]}-{date_months[utils.cleanup(month)]}-{year}) {gold_date} {note}")
        except:
            try:
                print(f"Text {text_id}: {day} {month} {year} ({cardinals[utils.cleanup(day)]}-{date_months[utils.cleanup(month)]}-{year}) {gold_date} {note}")
            except:
                if day != 0 and month != "" and year != 0:
                    clean_date = date_to_numeric(f"{day} {month} {year}")
                    print(f"Text {text_id}: {day} {month} {year} {clean_date} {gold_date} {clean_date == gold_date} {note}")
                    if not correct_death_date_found:
                        correct_death_date_found = clean_date == gold_date
                else:
                    utils.print_with_color(f"Text {text_id}: {day} {month} {year} {gold_date} {note}\n")
    return correct_death_date_found


def fix_years(text_id, dates_in):
    """ replace impossible years (< y-1 or > y) with the document year """
    try:
        target_year = int(text_id[:4])
    except:
        return dates_in
    dates_out = []
    for date_in in dates_in:
        date_in = list(date_in)
        if (len(date_in) == 0 or
            not re.search("^\d{4}$", str(date_in[-1])) or
            int(date_in[-1]) == target_year or
            int(date_in[-1]) == target_year-1):
            dates_out.append(date_in)
        else:
            utils.print_with_color(f"changing year {date_in[-1]} to {target_year}\n")
            date_in.pop(-1)
            date_in.append(str(target_year))
            dates_out.append(tuple(date_in))
    return dates_out


def get_document_date(text):
    """ get the date of a document using two patterns: 'heden' and 'heden den'"""
    dates = get_dates(text, "heden")
    if not dates:
        dates = get_dates(text, "heden den")
    return dates


def fix_missing_years(text, dates):
    """ add the year of a document to death dates compensate for missing death years """
    fixed_dates = []
    document_dates = get_document_date(text)
    for date in dates:
        if get_year_from_date(date) != 0:
            fixed_dates.append(date)
        elif (document_dates and 
              get_year_from_date(document_dates[0])!= 0 and 
              (get_day_from_date(date) != 0 or get_month_from_date(date) != "")):
            if date_months[utils.cleanup(get_month_from_date(document_dates[0]))] < date_months[utils.cleanup(get_month_from_date(date))]:
                fixed_dates.append((get_day_from_date(date), get_month_from_date(date), get_year_from_date(document_dates[0]) - 1))
            else:
                fixed_dates.append((get_day_from_date(date), get_month_from_date(date), get_year_from_date(document_dates[0])))
        elif not document_dates or get_year_from_date(document_dates[0]) == 0:
            if get_day_from_date(date) != 0 or get_month_from_date(date) != "" or get_year_from_date(date) != 0:
                fixed_dates.append(date)
    return fixed_dates


def get_death_date(text):
    """ extract a death date from a text using two patterns: 'op den' and 'op' """
    dates = get_dates(text, "op den")
    if not dates:
        death_dates = get_dates(text, "op")
        dates = fix_missing_years(text, death_dates)
    return dates
