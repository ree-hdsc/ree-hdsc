#!/usr/bin/env python3
# add_zeroes.py: standardize file name length by adding zeroes to file id
# usage: add_zeroes.py filenames
# 20230406 erikt(at)xs4all.nl

import os
import re
import sys

def update_filename(filename):
    try:
        fields_suffix = filename.split(".")
        fields_id = fields_suffix[-2].split(" ")
        if re.search("^\d+$", fields_id[-1]):
            updated_id = fields_id[-1].zfill(3)
            return ".".join(fields_suffix[:-2] + 
                            [" ".join(fields_id[:-1] + [updated_id])] + 
                            [fields_suffix[-1]])
    except:
        pass
    return filename

for filename in sys.argv[1:]:
    updated_filename = update_filename(filename)
    if updated_filename != filename:
        os.rename(filename, updated_filename)
