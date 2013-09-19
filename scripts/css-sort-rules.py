#!/usr/bin/env/python

import os
import re

CSS_DIR = '../media/css'
REGEX = re.compile('{\n(?:\s+[\w-]+: .*?;\n)+', re.MULTILINE)


def get_css_filenames():
    filenames = []
    for root, dirs, files in os.walk(CSS_DIR):
        for f in files:
            if f.endswith('.styl') or f.endswith('.less'):
                filenames.append(os.path.join(root, f))
    return filenames


def sort_rules(filename):
    f = open(filename, 'r+')
    contents = f.read()
    rule_sets = REGEX.findall(contents)
    for rule_set in rule_sets:
        indents = len(re.match('\s+', rule_set.split('\n')[1]).group(0))
        sorted_rules = sorted([r.strip() for r in rule_set.split('\n')[1:-1]])
        new_rule_set = format_rules(sorted_rules, indents)
        if rule_set != new_rule_set:
            f.seek(0)
            f.write(contents.replace(rule_set, new_rule_set))
            f.truncate()
    f.close()


def format_rules(rules, indents):
    """List of CSS rules to a string with line breaks and indents."""
    formatted_ruleset = '{\n'
    for rule in rules:
        formatted_ruleset += ' ' * indents + rule + '\n'
    return formatted_ruleset


def run():
    for filename in get_css_filenames():
        sort_rules(filename)


if __name__ == '__main__':
    run()
