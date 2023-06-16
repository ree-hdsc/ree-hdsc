import regex
import transformers
from . import utils

# Tested models (initial number indicates monthly downloads):
# (345) wietsedv/bert-base-dutch-cased-finetuned-conll2002-ner (several false positives)
# (74) Matthijsvanhof/bert-base-dutch-cased-finetuned-NER (not useful, tags everything)
# (16) wietsedv/bert-base-dutch-cased-finetuned-sonar-ner (some false positives)
# (13) proycon/bert-ner-cased-conll2002-nld (did not find any entities)
# (10) proycon/bert-ner-cased-sonar1-nld (found only one entity)
# (10) Matthijsvanhof/bert-base-dutch-cased-finetuned-NER8 (not useful, tags everything)
# (4) wietsedv/bert-base-dutch-cased-finetuned-udlassy-ner (few false positives) SELECTED

transformers.utils.logging.set_verbosity_error()
run_bert_pipeline = transformers.pipeline(task='ner', model='wietsedv/bert-base-dutch-cased-finetuned-udlassy-ner')


def show_names(entities):
    name = ""
    for part in entities:
        if regex.search("^B", part["entity"]) and name != "":
            print(name)
            name = ""
        if regex.search("(GPE|PERSON)$", part["entity"]):
            if name != "":
                name += " "
            name += part["word"]
    if name != "":
        print(name)


def expand_entities(entities_in, text):
    entities_out = []
    for entity_in in entities_in:
        entity_out = entity_in.copy()
        while (entity_out["end"] < len(text) and
               (regex.search("\w", text[entity_out["end"]]) or 
                regex.search("[.,-]", text[entity_out["end"]]))):
            entity_out["word"] += text[entity_out['end']]
            entity_out["end"] += 1
        entities_out.append(entity_out)
    return entities_out


def expand_last_entity(entities, entity):
    entities[-1]["word"] += " " + entity["word"]
    entities[-1]["end"] = entity["end"]


def combine_entities(entities_in):
    entities_out = []
    for entity_in in entities_in:
        entity_out = entity_in.copy()
        if len(entities_out) == 0:
            entities_out.append(entity_out)
        elif regex.search("^I-", entity_out["entity"]):
            expand_last_entity(entities_out, entity_out)
        else:
            entity_out["entity"] = regex.sub("^[BIE]-", "B-", entity_out["entity"])
            if entity_out["start"] < entities_out[-1]["start"]:
                print("error: entities are not sorted by position!")
            elif entity_out["start"] <= entities_out[-1]["end"] + 1 and entity_out["entity"] == entities_out[-1]["entity"]:
                expand_last_entity(entities_out, entity_out)
            else:
                entities_out.append(entity_out)
    return entities_out


def process_and_render_texts(texts):
    for text_id in texts:
        text = texts[text_id]
        entities = run_bert_pipeline(text)
        entities = combine_entities(expand_entities(entities, text))
        print(f"Text {text_id}")
        render_text(text, convert_guessed_entities(entities))


def cleanup(text_in):
    text_out = regex.sub("\s+", " ", text_in)
    text_out = regex.sub("- ", "", text_out)
    return regex.sub("[,.]", "", text_out.lower())


def compare_names(results, metadata):
    if len(results[0]) == 0 or results[0][0] == "":
        return True
    if "first_names" not in metadata or "last_name" not in metadata:
        return(False)
    guessed_name = results[0][0]
    if regex.search(".,.", guessed_name):
        guessed_name = regex.sub("^[^,]+, *(\S.*)$", "\\1", results[0][0]) + " " + regex.sub("^([^,]+),.*$", "\\1", results[0][0])
    annotated_name = " ".join([ metadata["first_names"], metadata["last_name"]])
    return cleanup(guessed_name) == cleanup(annotated_name)


def evaluate_deceased_names(results, nbr_of_names_found, nbr_of_stillborns_found, metadata):
    if len(results[0]) != 0 and regex.search("\w", results[0][0]):
        nbr_of_names_found += 1
    if results[1] > 0:
        nbr_of_stillborns_found += 1
    return nbr_of_names_found, nbr_of_stillborns_found, compare_names(results, metadata)


def get_metadata(metadata, text, keys):
    data = {}
    for key in keys:
        if key in metadata:
            for metadata_item in metadata[key]:
                name = text[int(metadata_item["offset"]): 
                            int(metadata_item["offset"]) + int(metadata_item["length"])]
                if key not in data:
                    data[key] = name
                else:
                    data[key] += " " + name
    return data


def print_name_correct(name_is_correct):
    if not name_is_correct:
        utils.print_with_color("wrong name")


def stillborn_count(text):
    return len(utils.find_text_patterns("levenloos", text))


def get_name_of_deceased_from_entities(text, entities):
    deceased = []
    deceased_positions = utils.find_text_patterns("overleden is:?,?", text) + utils.find_text_patterns("is overleden:?,?", text)
    for position in deceased_positions:
        name_deceased = ""
        for entity in entities:
            if entity["start"] == position["end"] + 1:
                name_deceased = entity["word"]
        deceased.append(name_deceased)
    return deceased


def get_next_token(entity, text):
    next_token = ""
    start_id = entity["end"]
    while start_id < len(text) and regex.search("\s", text[start_id]):
        start_id += 1
    end_id = start_id + 1
    while end_id < len(text) and regex.search("\S", text[end_id]):
        end_id += 1
    if start_id < len(text):
        next_token = text[start_id: end_id]
    return next_token, end_id


def combine_capitalized_words(entities, text):
    for i in range(0, len(entities)):
        if regex.search("(PERSON|GPE)", entities[i]["entity"]):
            next_token, end_id = get_next_token(entities[i], text)
            while next_token != "" and regex.search("^[A-Z]\\b", next_token) and not regex.search(",", text[entities[i]["start"]: entities[i]["end"]]):
                entities[i]["end"] = end_id
                entities[i]["word"] = text[entities[i]["start"]: entities[i]["end"]]
                next_token, end_id = get_next_token(entities[i], text)
    return entities


def get_entities_from_text(text):
    entities = run_bert_pipeline(text)
    entities = combine_entities(expand_entities(entities, text))
    entities = combine_capitalized_words(entities, text)
    return entities


def get_name_of_deceased_from_text(text):
    entities = get_entities_from_text(text)
    return get_name_of_deceased_from_entities(text, entities)
