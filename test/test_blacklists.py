#!/usr/bin/env python3
# coding=utf-8

import yaml
from os import unlink
import regex
from globalvars import GlobalVars

import pytest

from blacklists import Blacklist, YAMLParserCIDR, YAMLParserASN, YAMLParserNS, load_blacklists
from helpers import files_changed, blacklist_integrity_check, not_regex_search_ascii_and_unicode
from findspam import NUMBER_REGEX, NUMBER_REGEX_START, NUMBER_REGEX_END, NUMBER_REGEX_MINIMUM_DIGITS, NUMBER_REGEX_MAXIMUM_DIGITS


def test_number_lists():
    errors = []
    no_exacts = []

    def test_a_number_list(list_type, number_list):
        line_number = 0
        for pattern in number_list:
            line_number += 1
            digit_count = len(regex.findall(r'\d', pattern))
            digit_count_text = " ({} digits is OK)".format(digit_count)
            if digit_count < NUMBER_REGEX_MINIMUM_DIGITS or digit_count > NUMBER_REGEX_MAXIMUM_DIGITS:
                digit_count_text = ": {} digits is not >= {} and <= {}".format(digit_count, NUMBER_REGEX_MINIMUM_DIGITS, NUMBER_REGEX_MAXIMUM_DIGITS)
            if not_regex_search_ascii_and_unicode(NUMBER_REGEX, pattern):
                errors.append("{} number ({}): fails NUMBER_REGEX{}::{}".format(list_type, line_number, digit_count_text, pattern))
            else:
                this_no_exacts = []
                if not_regex_search_ascii_and_unicode(NUMBER_REGEX_START, pattern):
                    this_no_exacts.append("Does not match NUMBER_REGEX_START.")
                if not_regex_search_ascii_and_unicode(NUMBER_REGEX_END, pattern):
                    this_no_exacts.append("Does not match NUMBER_REGEX_END.")
                if len(this_no_exacts) > 0:
                    no_exact = "{} number ({}): ".format(list_type, line_number)
                    no_exact += " ".join(this_no_exacts) + digit_count_text + "::" + pattern
                    no_exacts.append(no_exact)

    load_blacklists()
    test_a_number_list("watched", GlobalVars.watched_numbers)
    test_a_number_list("blacklisted", GlobalVars.blacklisted_numbers)
    no_exacts_count = len(no_exacts)
    if (no_exacts_count > 0):
        pluralize = "" if no_exacts_count == 1 else "s"
        print("\n\t".join(["{} pattern{} can't match exactly:".format(no_exacts_count, pluralize)] + no_exacts))
    error_count = len(errors)
    if error_count > 0:
        pluralize = "" if error_count == 1 else "s"
        pytest.fail("\n\t".join(["{} error{} have occurred:".format(error_count, pluralize)] + errors))


def test_blacklist_integrity():
    errors = blacklist_integrity_check()

    if len(errors) == 1:
        pytest.fail(errors[0])
    elif len(errors) > 1:
        pytest.fail("\n\t".join(["{} errors have occurred:".format(len(errors))] + errors))


def test_remote_diff():
    file_set = set("abcdefg")
    true_diff = "a c k p"
    false_diff = "h j q t"
    assert files_changed(true_diff, file_set)
    assert not files_changed(false_diff, file_set)


def yaml_validate_existing(filename, cls):
    return Blacklist((filename, cls)).validate()


def test_yaml_blacklist():
    with open('test_ip.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_cidr',
            'Schema_version': '2019120601',
            'items': [
                {'ip': '1.2.3.4'},
                {'ip': '2.3.4.5', 'disable': True},
                {'ip': '3.4.5.6', 'comment': 'comment'},
            ]}, y)
    blacklist = Blacklist(('test_ip.yml', YAMLParserCIDR))
    with pytest.raises(ValueError) as e:
        blacklist.add('1.3.34')
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '1.2.3.4'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ip': '2.3.4.5'})
    with pytest.raises(ValueError) as e:
        blacklist.remove({'ip': '34.45.56.67'})
    blacklist.add({'ip': '1.3.4.5'})
    assert '1.2.3.4' in blacklist.parse()
    assert '2.3.4.5' not in blacklist.parse()
    assert '3.4.5.6' in blacklist.parse()
    blacklist.remove({'ip': '3.4.5.6'})
    assert '3.4.5.6' not in blacklist.parse()
    unlink('test_ip.yml')

    yaml_validate_existing('blacklisted_cidrs.yml', YAMLParserCIDR)
    yaml_validate_existing('watched_cidrs.yml', YAMLParserCIDR)


def test_yaml_asn():
    with open('test_asn.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_asn',
            'Schema_version': '2019120601',
            'items': [
                {'asn': '123'},
                {'asn': '234', 'disable': True},
                {'asn': '345', 'comment': 'comment'},
            ]}, y)
    blacklist = Blacklist(('test_asn.yml', YAMLParserASN))
    with pytest.raises(ValueError) as e:
        blacklist.add('123')
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': 'invalid'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '123'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'asn': '234'})
    with pytest.raises(ValueError) as e:
        blacklist.remove({'asn': '9897'})
    assert '123' in blacklist.parse()
    assert '234' not in blacklist.parse()
    assert '345' in blacklist.parse()
    blacklist.remove({'asn': '345'})
    assert '345' not in blacklist.parse()
    unlink('test_asn.yml')

    yaml_validate_existing('watched_asns.yml', YAMLParserASN)


def test_yaml_nses():
    with open('test_nses.yml', 'w') as y:
        yaml.dump({
            'Schema': 'yaml_ns',
            'Schema_version': '2019120601',
            'items': [
                {'ns': 'example.com.'},
                {'ns': 'example.net.', 'disable': True},
                {'ns': 'example.org.', 'comment': 'comment'},
            ]}, y)
    blacklist = Blacklist(('test_nses.yml', YAMLParserNS))
    assert 'example.com.' in blacklist.parse()
    assert 'EXAMPLE.COM.' not in blacklist.parse()
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'example.com.'})
    with pytest.raises(ValueError) as e:
        blacklist.add({'ns': 'EXAMPLE.COM.'})
    assert 'example.net.' not in blacklist.parse()
    assert 'example.org.' in blacklist.parse()
    blacklist.remove({'ns': 'example.org.'})
    assert 'example.org.' not in blacklist.parse()
    unlink('test_nses.yml')

    yaml_validate_existing('blacklisted_nses.yml', YAMLParserNS)
    yaml_validate_existing('watched_nses.yml', YAMLParserNS)
