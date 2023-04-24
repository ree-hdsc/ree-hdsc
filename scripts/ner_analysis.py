import transformers
from spacy import displacy

transformers.utils.logging.set_verbosity_error()

DEFAULT_MODEL = "wietsedv/bert-base-dutch-cased-finetuned-udlassy-ner'"


class NerAnalysis:

    def __init__(self, model=DEFAULT_MODEL):
        """create named entity recognition model"""
        self.named_entity_model = transformers.pipeline(task='ner', model=model)


    def expand_entities(entity_tokens_in, text):
        """expand entities with trailing unclassified characters"""
        entity_tokens_out = []
        for entity_token_in in entity_tokens_in:
            entity_token_out = entity_token_in.copy()
            while (entity_token_out["end"] < len(text) and 
                   (re.search("\w", text[entity_token_out["end"]]) or 
                    re.search("[.,-]", text[entity_token_out["end"]]))):
                entity_token_out["word"] += text[entity_token_out['end']]
                entity_token_out["end"] += 1
            entity_tokens_out.append(entity_token_out)
        return entity_tokens_out


    def expand_last_entity(entity_tokens, entity):
        """add entity to preceding entity"""
        entity_tokens[-1]["word"] += " " + entity["word"]
        entity_tokens[-1]["end"] = entity["end"]


    def combine_entity_neighbours(entity_tokens_in):
        """combine neighbouring entities"""
        entity_tokens_out = []
        for entity_token_in in entity_tokens_in:
            entity_token_out = entity_token_in.copy()
            if len(entity_tokens_out) == 0:
                entity_tokens_out.append(entity_token_out)
            elif re.search("^I-", entity_token_out["entity"]):
                self.expand_last_entity(entity_tokens_out, entity_token_out)
            else:
                entity_token_out["entity"] = re.sub("^[BIE]-", "B-", entity_token_out["entity"])
                if entity_token_out["start"] < entity_tokens_out[-1]["start"]:
                    print("error: entities are not sorted by position!")
                elif (entity_token_out["start"] <= entity_tokens_out[-1]["end"] + 1 and
                      entity_token_out["entity"] == entity_tokens_out[-1]["entity"]):
                    expand_last_entity(entity_tokens_out, entity_token_out)
                else:
                    entity_tokens_out.append(entity_token_out)
        return entity_tokens_out


    def process(text):
        """identify named entities in text"""
        entity_tokens = self.named_entity_model(text)
        entity_tokens = self.expand_entities(entity_tokens, text)
        entity_tokens = self.combine_entity_neighbours(entity_tokens)
        return entity_tokens


    def render_text(text, entities):
        """pretty-print entities in text"""
        displacy.render({ "text": re.sub("\\n", " ", text), 
                          "ents": entities }, 
                          options = { "colors": { "PERSON": "orange", 
                                                  "first_names": "orange", 
                                                  "last_name": "orange" } },
                                       style = "ent", 
                                       manual = True)
