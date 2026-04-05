"""
Sandboxed code execution engine.
Supports: Python, JavaScript (Node.js), Java, C, C++
Runs each test case with a timeout, captures stdout/stderr, compares output.
"""
import subprocess
import tempfile
import os
import time
import platform

TIMEOUT = 5  # seconds per test case
IS_WINDOWS = platform.system() == "Windows"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIMES_DIR = os.path.join(BASE_DIR, "runtimes")

if IS_WINDOWS:
    PYTHON_PATH = os.path.join(RUNTIMES_DIR, "python", "python.exe")
    NODEJS_PATH = os.path.join(RUNTIMES_DIR, "nodejs", "node-v20.11.1-win-x64", "node.exe")
    JAVA_PATH = os.path.join(RUNTIMES_DIR, "java", "jdk-21.0.2", "bin", "java.exe")
    JAVAC_PATH = os.path.join(RUNTIMES_DIR, "java", "jdk-21.0.2", "bin", "javac.exe")
    GCC_PATH = os.path.join(RUNTIMES_DIR, "mingw", "w64devkit", "bin", "gcc.exe")
    GPP_PATH = os.path.join(RUNTIMES_DIR, "mingw", "w64devkit", "bin", "g++.exe")
else:
    PYTHON_PATH = "python"
    NODEJS_PATH = "node"
    JAVA_PATH = "java"
    JAVAC_PATH = "javac"
    GCC_PATH = "gcc"
    GPP_PATH = "g++"

LANG_CONFIG = {
    "python": {
        "ext": ".py",
        "cmd": lambda path, _dir: [PYTHON_PATH, path],
        "compile": None,
    },
    "javascript": {
        "ext": ".js",
        "cmd": lambda path, _dir: [NODEJS_PATH, path],
        "compile": None,
    },
    "java": {
        "ext": ".java",
        "filename": "Main.java",
        "cmd": lambda _path, work_dir: [JAVA_PATH, "-cp", work_dir, "Main"],
        "compile": lambda path, work_dir: [JAVAC_PATH, path],
    },
    "c": {
        "ext": ".c",
        "cmd": lambda _path, work_dir: [os.path.join(work_dir, "a_out" if IS_WINDOWS else "a.out")],
        "compile": lambda path, work_dir: (
            [GCC_PATH, path, "-o", os.path.join(work_dir, "a_out")] if IS_WINDOWS
            else [GCC_PATH, path, "-o", os.path.join(work_dir, "a.out")]
        ),
    },
    "cpp": {
        "ext": ".cpp",
        "cmd": lambda _path, work_dir: [os.path.join(work_dir, "a_out" if IS_WINDOWS else "a.out")],
        "compile": lambda path, work_dir: (
            [GPP_PATH, path, "-o", os.path.join(work_dir, "a_out")] if IS_WINDOWS
            else [GPP_PATH, path, "-o", os.path.join(work_dir, "a.out")]
        ),
    },
}


def _execute(cmd, stdin_data, work_dir):
    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=work_dir
        )
        elapsed = time.time() - start
        return proc.stdout.strip(), proc.stderr.strip(), elapsed, None
    except subprocess.TimeoutExpired:
        return "", "Time Limit Exceeded", TIMEOUT, "TLE"
    except FileNotFoundError as e:
        return "", f"Runtime not found: {e}", 0, "RNF"
    except Exception as e:
        return "", str(e), 0, "ERR"


def run_code(code: str, language: str, test_cases: list) -> list:
    """
    Run `code` in `language` against each test case dict {input, output}.
    Returns list of result dicts.
    """
    lang = language.lower()
    if lang not in LANG_CONFIG:
        return [{"error": f"Unsupported language: {language}", "passed": False}]

    cfg = LANG_CONFIG[lang]
    results = []

    with tempfile.TemporaryDirectory() as work_dir:
        # Write source file
        fname = cfg.get("filename") or f"solution{cfg['ext']}"
        src_path = os.path.join(work_dir, fname)
        with open(src_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Compile if needed
        if cfg["compile"]:
            compile_cmd = cfg["compile"](src_path, work_dir)
            try:
                comp = subprocess.run(
                    compile_cmd,
                    capture_output=True, text=True, timeout=15, cwd=work_dir
                )
                if comp.returncode != 0:
                    return [{
                        "caseIndex": i,
                        "passed": False,
                        "error": "Compilation Error",
                        "stderr": comp.stderr,
                        "time": 0
                    } for i in range(len(test_cases))]
            except FileNotFoundError:
                compiler_name = compile_cmd[0]
                return [{
                    "caseIndex": i,
                    "passed": False,
                    "error": f"Compiler '{compiler_name}' not found on server",
                    "time": 0
                } for i in range(len(test_cases))]
            except subprocess.TimeoutExpired:
                return [{"caseIndex": i, "passed": False, "error": "Compilation Timeout", "time": 0}
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
                "error": err_type
            })

    return results
