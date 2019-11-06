"""
General idea of this script is to walk over all .cs files under the project directory, and list those that have more than x annotations
"""
import json
import re
import tempfile
import sys
import urllib.request
import multiprocessing
from zipfile import ZipFile
from os import scandir, path
from sys import argv

_An_re = re.compile(r"\[[A-z]\w+(\(.+\))*\]")
_Class_re = re.compile(r"(?<=class )[A-Z]\w+")
_Test_re = re.compile("test")
_Url_Project_re = re.compile(r"(?<=archive\/)(\w+)")
_Url_Archive_re = re.compile(r"(?<=archive\/)\w+\.zip")
_Min_annotations = 3
_tests = "tests"
_results = "results"
_best_matches = "best_matches"
_download_dir = None
_results_dir = None


def _get_class_name(file_path: str):
    try_again = False
    lines = None
    cname = ""
    #I'm reading src code so it's safe to read it all at once
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
                print("match found")
                cname = match.group(0)
    return cname


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
                    if entry.is_file() and len(path.splitext(entry.name)) is 2 and path.splitext(entry.name)[1] == ".cs":
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
            try:
                r = _path_walker(dir)
                results[_tests] += r[_tests]
                results[_results] += r[_results]
            except:
                print("Unexpected error.")
    return results

def _generic_assert_equals(name, expected, result):
    if expected == result:
        print(f"ok {name}")
    else:
        print(f"failed {name}", f" expected {str(expected)}; got {result}")

def _test_get_class_name():
    result = _get_class_name("ScriptT/ImASrcFolder/IHaveAnnotations.cs")
    expected = "IHaveAnnotations"
    _generic_assert_equals("_test_get_class_name",expected, result)

#Fixme
def _test_path_walker():
    r = _path_walker("ScriptT")
    ok =  "ImAtestFolder" in r[_tests][0] and "IHaveAnnotations" in r[_results][0]
    if ok:
        print("ok _test_path_walker")
    else:
        print(f"failed _test_path_walker expected  \"ImAtestFolder\" in r[_tests][0] and \"IHaveAnnotations\" in r[_results][0]",
              f" got {r[_tests][0]} and {r[_results][0]}")


def _test_find_best_matches():
    r = _path_walker("ScriptT")
    w_best_matches = _find_best_matches(r)
    print(w_best_matches)


def walk(directory, save_results_in=path.realpath(__file__), save_as="results.txt", min_annotations=3,
         get_best_matches=True):
    global _Min_annotations
    save_at = path.normpath(save_results_in + "/" + save_as)
    _Min_annotations = min_annotations
    results = _path_walker(path.normpath(directory))
    if get_best_matches:
        results = _find_best_matches(results)
    if len(results[_best_matches]) > 0:
        print(save_at + " will have best matches.")
    with open(save_at, "w", errors="ignore") as results_file:
        results_file.write(json.dumps(results, indent=4, sort_keys=True))

def test():
    _test_find_best_matches()
    _test_get_class_name()
    _test_path_walker()


def _download_and_walk(url :str):
    global _download_dir
    global _results_dir
    download_dir = _download_dir
    download_dir = results_dir = _results_dir
    project_name = _Url_Project_re.search(url).group(0).replace("/", ".")
    project_name_zip = project_name + _Url_Archive_re.search(url).group(0)
    print(f"Downloading {project_name_zip} to {download_dir}")
    file_name,_ = urllib.request.urlretrieve(url, path.normpath(download_path+project_name_zip))
    print(f"Finished downloading {url}")
    print(f"Walking {project_name}")
    # Walk right ahead because in a concurrent model, walk needs download result and urlretrieve is blocking already
    try:
        walk(download_dir, save_results_in=results_dir, save_as=project_name + ".json")
    except Error as err:
        print(f"Unexpected error when walking {project_name}", err)

    print(f"Finished walking {project_name}")


def main():
    """Script mode stuff"""
    args = [path.normpath(x) for x in argv[1:]]
    results_dir = tempfile.mkdtemp()
    print(f"Results will be saved at {results_dir}")
    pool = multiprocessing.Pool()
    with tempfile.TemporaryDirectory() as download_dir:  # With clause so downloaded zip files are always deleted
        _download_dir = download_dir
        _results_dir = results_dir
        for arg in args:
            if path.isfile(arg):
                with open(arg, "r") as arg_file:
                    urls = arg_file.readlines()
                    pool.map(_download_and_walk, urls)
            else:
                print(f"{arg} doesnt exists.")
        download_dir.cleanup()

main()
