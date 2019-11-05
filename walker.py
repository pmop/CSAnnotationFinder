"""
General idea of this script is walk in all .cs files under directory and list those that have more than x annotations
"""
import json
import re
import tempfile
import wget
import sys
from zipfile import ZipFile
from os import scandir, path
from sys import argv
from typing import TextIO

_An_re = re.compile("\[[A-Z][A-z]+.+\]")
_Class_re = re.compile(f"[\w ]+class (\w+)")
_Test_re = re.compile("test")
_Min_annotations = 3
_tests = "tests"
_results = "results"
_best_matches = "best_matches"


def _get_class_name(file_path: str, encoding="utf8"):
    try_again = False
    try:
        with open(file_path, "r") as class_file:
            for line in class_file.readlines():
                match = _Class_re.search(line)
                if match:
                    return match.group(1)
    except:
        print("Unexpected error", sys.exc_info()[0])
        if encoding == "utf8":
            encoding = "iso-8859-1"
            try_again = True
        else:
            raise IOError
    if try_again:
        _get_class_name(file_path, encoding)


def _find_best_matches(result: dict):
    test_folders = result[_tests]
    files_w_annotations = result[_results]
    best_matches = []
    for f in files_w_annotations:
        class_name = None
        try:
            class_name = _get_class_name(f)
        except IOError:
            print("Unable to recover the classname for file: ", f)
        if class_name is not None:
            class_name_re = re.compile(f".+" + class_name + ".+")
            best_match = {"class": class_name,
                          _tests: []}
            for t in test_folders:
                for entry in scandir(t):
                    if entry.is_file() and len(path.splitext(entry.name)) is 2 and path.splitext(entry.name)[
                        1] == ".cs":
                        try:
                            with open(entry.path) as entry_file:
                                for l in entry_file.readlines():
                                    if class_name_re.search(l):
                                        best_match[_tests].append(entry.path)
                                        break
                        except:
                            print(f"Unexpected error: unable to read {entry.path}. Reason:", sys.exc_info()[0])
            if len(best_match[_tests]) > 0:
                best_matches.append(best_match)
    if len(best_matches) > 0:
        result[_best_matches] += best_matches
    return result


def _path_walker(where: str):
    global _Min_annotations
    results = {
        _tests: [],
        _results: [],
        _best_matches: []
    }
    try:
        entries_gen = scandir(where)
        entries = [x for x in entries_gen]
        csfiles = filter(lambda x: x.is_file() and len(path.splitext(x.name)) is 2 and path.splitext(x.name)[1] == ".cs",
                         entries)
        dirs = filter(lambda x: x.is_dir() and not str(x.name).startswith("."), entries)
        for f in csfiles:
            with open(f, "r", errors="ignore") as _file:
                matches = set()
                for line in _file.readlines():
                    match = _An_re.search(line)
                    if match:
                        matches.add(match.group(0))
                if len(matches) == _Min_annotations:
                    results[_results].append(f.path)
                    break

        for dir in dirs:
            if _Test_re.search(dir.path.lower()):
                results[_tests].append(dir.path)
            else:
                r = _path_walker(dir)
                results[_tests] += r[_tests]
                results[_results] += r[_results]
        return results
    except (TypeError, FileNotFoundError, IOError) as error:
        print (f"Unable to walk over {where}", error)
    except:
        print ("Unexpected error", sys.exc_info()[0])
    finally:
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


def walk(directory, save_results_in=path.realpath(__file__), save_as="results.txt", min_annotations=3,
         get_best_matches=True):
    global _Min_annotations
    _Min_annotations = min_annotations
    results = _path_walker(path.normpath(directory))
    if get_best_matches:
        results = _find_best_matches(results)
    if len(results[_best_matches]) > 0:
        print(save_results_in + " will have best matches.")
    with open(path.normpath(save_results_in + "/" + save_as), "w", errors="ignore") as results_file:
        results_file.write(json.dumps(results, indent=4, sort_keys=True))


"""Script mode stuff"""
args = [path.normpath(x) for x in argv[1:]]
results_dir = tempfile.mkdtemp()
print(f"Results will be saved at {results_dir}")
with tempfile.TemporaryDirectory() as download_dir: # With clause so downloaded zip files are always deleted
    for arg in args:
        if path.isfile(arg):
            with open(arg, "r") as arg_file:
                for line in arg_file.readlines():
                    file_name = path.normpath(wget.download(line.strip(), download_dir))
                    try:
                        with ZipFile(file_name) as zipfile:
                            zipfile.extractall(path=download_dir)
                        print("Walking " + file_name + " at " + file_name)
                        walk(download_dir, save_results_in=results_dir, save_as=path.basename(file_name) + "_results.json")
                    except (TypeError, FileNotFoundError, IOError) as err:
                        print(f"Error: Could'nt walk {file_name}", err)
                    except:
                        print(f"Unexpected error: Could'nt walk {file_name}", sys.exc_info()[0])

        else:
            print(f"{arg} doesnt exists.")
