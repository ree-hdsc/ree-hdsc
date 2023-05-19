import re
import transformers


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
        if re.search("^B", part["entity"]) and name != "":
            print(name)
            name = ""
        if re.search("(GPE|PERSON)$", part["entity"]):
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
               (re.search("\w", text[entity_out["end"]]) or re.search("[.,-]", text[entity_out["end"]]))):
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
        elif re.search("^I-", entity_out["entity"]):
            expand_last_entity(entities_out, entity_out)
        else:
            entity_out["entity"] = re.sub("^[BIE]-", "B-", entity_out["entity"])
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
    text_out = re.sub("\s+", " ", text_in)
    text_out = re.sub("- ", "", text_out)
    return re.sub("[,.]", "", text_out.lower())


def find_text_patterns(query, text):
    positions = []
    pattern = re.compile(query)
    for m in pattern.finditer(text.lower()):
        positions.append({"start": m.start(), "end": m.end()})
    return positions


def compare_names(results, metadata):
    if len(results[0]) == 0 or results[0][0] == "":
        return True
    if "first_names" not in metadata or "last_name" not in metadata:
        return(False)
    guessed_name = results[0][0]
    if re.search(".,.", guessed_name):
        guessed_name = re.sub("^[^,]+, *(\S.*)$", "\\1", results[0][0]) + " " + re.sub("^([^,]+),.*$", "\\1", results[0][0])
    annotated_name = " ".join([ metadata["first_names"], metadata["last_name"]])
    return cleanup(guessed_name) == cleanup(annotated_name)


def evaluate_deceased_names(results, nbr_of_names_found, nbr_of_stillborns_found, metadata):
    if len(results[0]) != 0 and re.search("\w", results[0][0]):
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
    return len(find_text_patterns("levenloos", text))


def get_name_of_deceased_from_entities(text, entities):
    deceased = []
    deceased_positions = find_text_patterns("overleden is:?,?", text) + find_text_patterns("is overleden:?,?", text)
    for position in deceased_positions:
        name_deceased = ""
        for entity in entities:
            if entity["start"] == position["end"] + 1:
                name_deceased = entity["word"]
        deceased.append(name_deceased)
    return deceased


def get_name_of_deceased_from_text(text):
    entities = run_bert_pipeline(text)
    entities = combine_entities(expand_entities(entities, text))
    return get_name_of_deceased_from_entities(text, entities)
