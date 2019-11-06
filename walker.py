"""
General idea of this script is to walk over all .cs files under the project directory, and list those that have more than x annotations
"""
import json
import re
import os
import tempfile
import sys
import urllib.request
import zipfile
import multiprocessing
from os import scandir, path
from sys import argv

_An_re = re.compile(r"\[([A-Z]\w+).+\]")
_Class_re = re.compile(r"(?<=class )[A-Z]\w+")
_Test_re = re.compile("test")
_Url_Project_re = re.compile(r"(?<=.com\/)\w+\/\w+")
_Url_Archive_re = re.compile(r"\w+\.zip")
_Min_annotations = 3
_tests = "tests"
_results = "results"
_best_matches = "best_matches"
_annotations_matches = "annotations_matches"
_results_dir = None


def _get_class_name(file_path: str):
    try_again = False
    lines = None
    cname = ""
    # I'm reading src code so it's safe to read it all at once
    try:
        with open(file_path, "r", errors="replace") as file:
            lines = file.readlines()
    except (IOError, FileNotFoundError, UnicodeDecodeError) as err:
        print("failure at _get_class_name ", err)
    except:
        print("unexpected failure at _get_class_name ")
    if lines:
        for line in lines:
            match = _Class_re.search(line)
            if match:
                cname = match.group(0)
    return cname


def _find_best_matches(result_dict: dict):
    test_paths_list = result_dict[_tests]
    results_list = result_dict[_results]  # list of dictionaries
    best_matches = []
    for result in results_list:
        cname = None
        _path = result[_results]
        try:
            cname = _get_class_name(_path)
        except IOError:
            print("Unable to recover the classname for file: ", _path)
        if cname is not None:
            best_match = {
                "class": cname,
                "path": _path,
                "annotations": result[_annotations_matches],
                _tests: []
            }
            find_class_use_in_code = re.compile(f".+" + cname + ".+")
            for test_path in test_paths_list:
                for test_dir_entry in scandir(test_path):
                    # depth 1 search
                    if test_dir_entry.is_file() and (len(path.splitext(test_dir_entry.name)) is 2) and \
                            (path.splitext(test_dir_entry.name)[1] == ".cs"):
                        try:
                            with open(test_dir_entry.path) as test_file:
                                for line in test_file.readlines():
                                    if find_class_use_in_code.search(line):
                                        best_match[_tests].append(test_dir_entry.path)
                                        break  # proceed to search in the next test file
                        except:
                            print(
                                f"Unexpected error when trying to read the test file {test_dir_entry.result}. Reason:",
                                sys.exc_info()[0])
            if len(best_match[_tests]) > 0:
                best_matches.append(best_match)
    if len(best_matches) > 0:
        result_dict[_best_matches] += best_matches
    return result_dict


def _path_walker(where: str):
    global _Min_annotations
    results = {
        _tests: [],
        _results: [],
        _best_matches: [],
    }
    entries_gen = scandir(where)
    entries = [x for x in entries_gen]
    csfiles = filter(
        lambda x: x.is_file() and len(path.splitext(x.name)) is 2 and path.splitext(x.name)[1] == ".cs",
        entries)
    dirs = filter(lambda x: x.is_dir() and not str(x.name).startswith("."), entries)
    for f in csfiles:
        with open(f, "r", errors="ignore") as _file:
            matches = set()
            for line in _file.readlines():
                if line.strip().startswith("//"):
                    break
                match = _An_re.search(line)
                if match:
                    matches.add(match.group(0))
                if len(matches) == _Min_annotations:
                    r = {
                        _results: f.path,
                        _annotations_matches: str(list(matches))
                    }
                    results[_results].append(r)
                    break
    for dir in dirs:
        if _Test_re.search(dir.path.lower()):
            results[_tests].append(dir.path)
        else:
            try:
                r = _path_walker(dir)
                results[_tests] += r[_tests]
                results[_results] += r[_results]
            except:
                print("Unexpected error.")
    return results


def walk(directory, save_results_in=path.realpath(__file__), save_as="results.txt", min_annotations=3,
         get_best_matches=True):
    global _Min_annotations
    save_at = path.normpath(save_results_in + "/" + save_as)
    if path.isfile(save_at):
        print(save_at + " has been walked before. Ignoring.")
        return
    _Min_annotations = min_annotations
    results = _path_walker(path.normpath(directory))
    if get_best_matches:
        results = _find_best_matches(results)
    if len(results[_best_matches]) > 0:
        print(save_at + " will have best matches.")
    with open(save_at, "w", errors="ignore") as results_file:
        results_file.write(json.dumps(results, indent=4, sort_keys=True))


def _generic_assert_equals(name, expected, result):
    if expected == result:
        print(f"ok {name}")
    else:
        print(f"failed {name}", f" expected {str(expected)}; got {result}")


def _test_get_class_name():
    result = _get_class_name("ScriptT/ImASrcFolder/IHaveAnnotations.cs")
    expected = "IHaveAnnotations"
    _generic_assert_equals("_test_get_class_name", expected, result)


def _test_path_walker():
    r = _path_walker("ScriptT")
    ok = "ImAtestFolder" in r[_tests][0] and "IHaveAnnotations" in r[_results][0][_results]
    if ok:
        print("ok _test_path_walker")
    else:
        print(
            f"failed _test_path_walker expected  \"ImAtestFolder\" in r[_tests][0] and \"IHaveAnnotations\" in r[_results][0]",
            f" got {r[_tests][0]} and {r[_results][0][_results]}")


def _test_find_best_matches():
    r = _path_walker("ScriptT")
    w_best_matches = _find_best_matches(r)
    print(w_best_matches)


def _test_url_regexes():
    url = "https://github.com/test/Test/master.zip"
    prj = _Url_Project_re.search(url).group(0)
    archive = _Url_Archive_re.search(url).group(0)
    if prj == "test/Test" and archive == "master.zip":
        print("ok _test_url_regexes")
    else:
        print("failure _test_url_regexes")
        print(f"expected test/Test, got {prj}", f"expected master.zip, got {archive}")


def test():
    _test_find_best_matches()
    _test_get_class_name()
    _test_path_walker()
    _test_url_regexes()


def _download_and_walk(url: str):
    global _results_dir
    results_dir = _results_dir
    url = url.strip()
    file_name = None
    project_name = _Url_Project_re.search(url).group(0).replace("/", ".")
    project_name_zip = project_name + _Url_Archive_re.search(url).group(0)
    with tempfile.TemporaryDirectory() as download_dir:
        print(f"Downloading {project_name_zip} to {download_dir}")
        try:
            file_name, _ = urllib.request.urlretrieve(url, path.normpath(download_dir + project_name_zip))
            print(f"Finished downloading {url}")
        except:
            print(f"Unexpected error when trying to download {project_name}")
        if file_name:
            print(f"Walking {project_name}")
    # Walk right ahead because in a concurrent model, walk needs download result and urlretrieve is blocking already
            try:
                with zipfile.ZipFile(file_name, "r") as zip_ref:
                    zip_ref.extractall(path=download_dir)
                    walk(download_dir, save_results_in=results_dir, save_as=project_name + ".json")
            except:
                print(f"Unexpected error when walking {project_name}")
            print(f"Finished walking {project_name}")


# Script mode stuff
def main():
    global _results_dir
    args = [path.normpath(x) for x in argv[1:]]
    current_path = path.dirname(path.realpath(__file__))
    results_dir = path.normpath(current_path + "/" + "results")
    if not path.isdir(results_dir):
        os.mkdir(results_dir)

    print(f"Results will be saved at {results_dir}")
    # pool = multiprocessing.Pool()
    _results_dir = results_dir
    for arg in args:
        if path.isfile(arg):
            with open(arg, "r") as arg_file:
                urls = arg_file.readlines()
                _ = [_download_and_walk(url) for url in urls]
                # pool.map(_download_and_walk, urls)
        else:
            print(f"{arg} doesnt exists.")


main()
