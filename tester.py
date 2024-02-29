import os
import sys
import argparse
import logging.handlers
import propaganda.src.annotation as an
import propaganda.src.annotations as ans
import propaganda.src.propaganda_techniques as pt

def datadup(directory):
    first_lines = []
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        if os.path.isfile(f):
            fline=open(f, encoding="utf8").readline().rstrip()
            first_lines += [[fline]]
        dupes = [x for n, x in enumerate(first_lines) if x in first_lines[:n]]
    print(dupes)
    if dupes == []:
        return False
    else:
        return True
    
def annotate(directory):
    for filename in os.listdir(directory):
        f = os.path.join(directory, filename)
        if os.path.isfile(f):
            user_annotations = ans.Annotations()
            user_annotations.load_annotation_list_from_file(f)
            print(user_annotations)

print(datadup('datasets/dev-articles'))
annotate('datasets/test-articles/')