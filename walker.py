"""
General idea of this script is walk in all .cs files under directory and list those that have more than x annotations
"""
from sys import argv
from os import scandir, path
import re
import json
An_re = re.compile("\[[A-z]+.+\]")
Class_re = re.compile(f"[\w ]+class (\w+)")
Test_re = re.compile("test")
Min_annotations = 3

_tests = "tests"
_results = "results"
_best_matches = "best_matches"


def _get_class_name(file_path : str):
    with open(file_path,"r") as class_file:
        for line in class_file.readlines():
            match = Class_re.search(line)
            if match:
                return match.group(1)


def _find_best_matches(result : dict):
    test_folders = result[_tests]
    files_w_annotations = result[_results]
    best_matches = []
    for f in files_w_annotations:
        class_name = _get_class_name(f)
        class_name_re = re.compile(f".+" + class_name +".+")
        best_match = {"class":class_name,
                      _tests: []}
        for t in test_folders:
            for entry in scandir(t):
                if entry.is_file() and path.splitext(entry.name)[1] == ".cs":
                    with open(entry.path) as entry_file:
                        for l in entry_file.readlines():
                            if class_name_re.search(l):
                                best_match[_tests].append(entry.path)
                                break
        if len(best_match[_tests]) > 0:
            best_matches.append(best_match)
    if len(best_matches) > 0:
        result[_best_matches] += best_matches
    return result




def _path_walker(where : str):
    global Min_annotations
    entries_gen = scandir(where)
    entries = [x for x in entries_gen]
    csfiles = filter(lambda x: x.is_file() and path.splitext(x.name)[1] == ".cs", entries)
    dirs = filter(lambda x: x.is_dir() and not str(x.name).startswith("."), entries)
    results = {
        _tests:  [],
        _results: [],
        _best_matches:[]
    }

    for f in csfiles:
        with open(f,"r") as _file:
            matches = set()
            for line in _file.readlines():
                match = An_re.search(line)
                if match:
                    matches.add(match.group(0))
            if len(matches) == Min_annotations:
                results[_results].append(f.path)
                break

    for dir in dirs:
        if Test_re.search(dir.path.lower()):
            results[_tests].append(dir.path)
        else:
            r = _path_walker(dir)
            results[_tests] += r[_tests]
            results[_results] += r[_results]
    return results

def _test_get_class_name():
    return _get_class_name("ScriptT/ImASrcFolder/IHaveAnnotations.cs") == "IHaveAnnotations"

def _test_path_walker():
    r = _path_walker(r"C:\Users\Pedro\PycharmProjects\annotationsfinder\ScriptT")
    return "ImAtestFolder" in r[_tests][0] and "IHaveAnnotations" in r[_results][0]

def _test_find_best_matches():
    r = _path_walker(r"C:\Users\Pedro\PycharmProjects\annotationsfinder\ScriptT")
    w_best_matches = _find_best_matches(r)
    print(w_best_matches)

def walk(directory, save_results_in=path.realpath(__file__), min_annotations = 3, get_best_matches = True):
    global Min_annotations
    Min_annotations = min_annotations

    results = _path_walker(path.normpath(directory))
    if get_best_matches:
        results = _find_best_matches(results)
    with open(path.normpath(save_results_in+"results.txt"), "w") as results_file:
        results_file.write(json.dumps(results))

