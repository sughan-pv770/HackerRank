import subprocess
import tempfile
import os
import time
import shutil

TIMEOUT = 5

def _find(binary):
    return shutil.which(binary) or binary

LANG_CONFIG = {
    "python": {
        "ext": ".py",
        "compile": None,
        "cmd": lambda path, _dir: [_find("python3"), path],
    },
    "javascript": {
        "ext": ".js",
        "compile": None,
        "cmd": lambda path, _dir: [_find("node"), path],
    },
    "java": {
        "ext": ".java",
        "filename": "Main.java",
        "compile": lambda path, work_dir: [_find("javac"), path],
        "cmd": lambda _path, work_dir: [_find("java"), "-cp", work_dir, "Main"],
    },
    "c": {
        "ext": ".c",
        "compile": lambda path, work_dir: [
            _find("gcc"), path, "-o", os.path.join(work_dir, "a.out"), "-lm"
        ],
        "cmd": lambda _path, work_dir: [os.path.join(work_dir, "a.out")],
    },
    "cpp": {
        "ext": ".cpp",
        "compile": lambda path, work_dir: [
            _find("g++"), path, "-o", os.path.join(work_dir, "a.out"), "-lm"
        ],
        "cmd": lambda _path, work_dir: [os.path.join(work_dir, "a.out")],
    },
}

LANG_ALIASES = {
    "c++": "cpp",
    "js": "javascript",
    "node": "javascript",
    "py": "python",
    "python3": "python",
}

def _execute(cmd, stdin_data, work_dir):
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, input=stdin_data, capture_output=True,
            text=True, timeout=TIMEOUT, cwd=work_dir,
        )
        elapsed = time.time() - start
        return proc.stdout.strip(), proc.stderr.strip(), elapsed, None
    except subprocess.TimeoutExpired:
        return "", "Time Limit Exceeded", TIMEOUT, "TLE"
    except FileNotFoundError as exc:
        return "", f"Runtime not found: {exc}", 0, "RNF"
    except Exception as exc:
        return "", str(exc), 0, "ERR"

def run_code(code: str, language: str, test_cases: list) -> list:
    lang = language.lower().strip()
    lang = LANG_ALIASES.get(lang, lang)

    if lang not in LANG_CONFIG:
        return [{"caseIndex": i, "passed": False,
                 "error": f"Unsupported language: '{language}'", "time": 0}
                for i in range(len(test_cases))]

    cfg = LANG_CONFIG[lang]
    results = []

    with tempfile.TemporaryDirectory() as work_dir:
        fname = cfg.get("filename") or f"solution{cfg['ext']}"
        src_path = os.path.join(work_dir, fname)
        with open(src_path, "w", encoding="utf-8") as fh:
            fh.write(code)

        if cfg["compile"]:
            compile_cmd = cfg["compile"](src_path, work_dir)
            try:
                comp = subprocess.run(
                    compile_cmd, capture_output=True,
                    text=True, timeout=30, cwd=work_dir,
                )
                if comp.returncode != 0:
                    return [{"caseIndex": i, "passed": False,
                             "error": "Compilation Error", "stderr": comp.stderr, "time": 0}
                            for i in range(len(test_cases))]
            except FileNotFoundError:
                return [{"caseIndex": i, "passed": False,
                         "error": f"Compiler not found. Contact administrator.", "time": 0}
                        for i in range(len(test_cases))]
            except subprocess.TimeoutExpired:
                return [{"caseIndex": i, "passed": False,
                         "error": "Compilation Timeout", "time": 0}
                        for i in range(len(test_cases))]

        run_cmd = cfg["cmd"](src_path, work_dir)

        for idx, tc in enumerate(test_cases):
            stdin_data = tc.get("input", "")
            expected = tc.get("output", "").strip()
            stdout, stderr, elapsed, err_type = _execute(run_cmd, stdin_data, work_dir)
            passed = (stdout == expected) and not err_type
            results.append({
                "caseIndex": idx,
                "input": stdin_data,
                "expected": expected,
                "actual": stdout,
                "passed": passed,
                "time": round(elapsed, 3),
                "stderr": stderr if not passed else "",
                "error": err_type,
            })

    return results
