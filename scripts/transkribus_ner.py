#!/usr/bin/env python3
# transkribus_ner: convert Transkribus HTR output (xml) to html files with named entity annotation
# usage: ./transkribus_ner xml_directory
# 20230322 e.tjongkimsang@esciencecenter.nl


import read_transkribus_files
import regex
import printed_text
import spacy
import sys
import utils


def read_files(data_dir_htr):
    texts_htr, metadata_htr, textregions_htr  = read_transkribus_files.read_files(data_dir_htr)
    for file_name in texts_htr:
        texts_htr[file_name] = "".join(texts_htr[file_name])
    return texts_htr


def get_token_positions(tokens):
    return [ { "start": token.idx, "end": token.idx + len(token) } for token in tokens ]


def get_spacy_entities(analysis):
    token_positions = get_token_positions([ token for token in analysis ])
    return [ { "start": token_positions[entity.start]["start"], 
               "end": token_positions[entity.end - 1]["end"],  
               "label": str(entity.label_) }
             for entity in analysis.ents ]


def get_next_token(text, position):
    index = position
    while index < len(text) and (regex.search("\s", text[index]) or text[index] == ","):
        index += 1
    next_token = ""
    while index < len(text) and regex.search("\S", text[index]):
        next_token += text[index]
        index += 1
    return next_token, index


def get_previous_token(text, position):
    index = position
    while index > 0 and regex.search("\s", text[index - 1]):
        index -= 1
    previous_token = ""
    while index > 0 and regex.search("\S", text[index - 1]):
        index -= 1
        previous_token = text[index] + previous_token
    return previous_token, index


def expand_entities(entities, text):
    for entity in entities:
        if entity["label"] == "PERSON":
            previous_token, previous_start = get_previous_token(text, entity["start"])
            while len(previous_token) > 0 and previous_token[0].isupper() and previous_token not in SKIP_TOKENS:
                entity["start"] = previous_start
                previous_token, previous_start = get_previous_token(text, entity["start"])
            next_token, next_end = get_next_token(text, entity["end"])
            while len(next_token) > 0  and next_token[0].isupper() and next_token not in SKIP_TOKENS:
                entity["end"] = next_end
                next_token, next_end = get_next_token(text, entity["end"])
    return entities

SKIP_TOKENS = [ "Oud", "En", "Een", "Twee", "Drie", "Vier", "Vijf", "Zes", "Zeven", "Acht", "Negen", "Tien", "in",
                "Ongehuwd", "Aanteekeningen.", "Aanteekeningen", "Verbeteringen.", "Hospitaal", "Compareerden", "De", "Sep",
                "No.", "Nr.", "Fol.", "Werk", "Heden", "Waarvan", "Jaars", "des", "January", "Januari", "February", "Februari",
                "Maart", "April", "Mei", "Juni", "Juli", "July", "Augustus", "September", "October", "November", "December",
                "Zeventienden",  "Zestienden", "Curaçao", "Curacao", "Habana", "Achthonderd", "Negenhonderd", "en",
                "Twintig", "Dertig", "Veertig", "Vijftig", "Zestig", "Zeventig", "Tachtig", "Negentig", "Honderd",  ]


def shrink_entities(entities, text):
    for entity in entities:
        if entity["label"] == "PERSON":
            final_token, next_end = get_previous_token(text, entity["end"])
            while len(final_token) > 0 and (final_token[0].islower() or final_token in SKIP_TOKENS or final_token[0].isdigit()):
                entity["end"] = next_end
                final_token, next_end = get_previous_token(text, entity["end"])
            first_token, next_start = get_next_token(text, entity["start"])
            while len(first_token) > 0 and (first_token[0].islower() or first_token in SKIP_TOKENS or first_token[0].isdigit()):
                entity["start"] = next_start
                first_token, next_start = get_next_token(text, entity["start"])
    return entities


LABEL_COLORS = {
   'CARDINAL': "lightblue", 
   'DATE': "lightblue", 
   'EVENT': "yellow", 
   'FAC': "lightgreen", 
   'GPE': "lightgreen", 
   'LANGUAGE': "yellow", 
   'LAW': "yellow", 
   'LOC': "lightgreen", 
   'MONEY': "brown", 
   'NORP': "lightblue", 
   'ORDINAL': "brown", 
   'ORG': "lightblue", 
   'PERCENT': "brown", 
   'PERSON': "pink", 
   'PRODUCT': "yellow", 
   'QUANTITY': "brown", 
   'TIME': "brown", 
   'WORK_OF_ART': "yellow"
}

nlp = spacy.load("nl_core_news_sm")
texts_htr = read_files("../notebooks/tmp/1764846/Sample_test_1/page/")
text_id = "p001.xml"
text = texts_htr[text_id]
analysis = nlp(text)
entities = get_spacy_entities(nlp(text))
entities = shrink_entities(expand_entities(entities, text), text)

last_start = len(text) + 1
for entity_id in range(len(entities) - 1, -1, -1):
    start = entities[entity_id]["start"]
    if start >= last_start:
        sys.exit(f"entities out of order: cannot happen: {start} {last_start} {entities}")
    end = entities[entity_id]["end"]
    if end > last_start:
        end = last_start
    label = entities[entity_id]["label"]
    text = text[:end] + f'</font><sub><font style="color: lightgrey">{label}</font></sub>' + text[end:]
    text = text[:start] + f'<font style="background-color: {LABEL_COLORS[label]}">'+ text[start:]
    last_start = start
text = regex.sub("\n", "<br>", text)
file_id = open(regex.sub("xml", "html", text_id), "w")
print(f"<html><body>{text}</body></html>", file=file_id)
file_id.close()
