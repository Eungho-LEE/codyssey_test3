"""Run the submitted program in isolated directories; keep actual output records."""
import copy
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "records"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "main.py"
    compile(source.read_text(encoding="utf-8"), str(source), "exec")
    spec = importlib.util.spec_from_file_location("submission", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads((ROOT / "data.json").read_text(encoding="utf-8-sig"))
    results = []

    def check(name, condition):
        results.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def run(name, inputs, expected, data=original):
        with tempfile.TemporaryDirectory(prefix="mini-npu-") as folder:
            path = Path(folder)
            shutil.copy2(source, path / "main.py")
            if data is not None:
                text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
                (path / "data.json").write_text(text, encoding="utf-8")
            process = subprocess.run([sys.executable, str(path / "main.py")],
                                     input=inputs, text=True, capture_output=True,
                                     cwd=path, timeout=20)
            (OUT / (name + ".txt")).write_text(
                "[STDIN]\n" + inputs + "\n[STDOUT]\n" + process.stdout
                + "\n[STDERR]\n" + process.stderr, encoding="utf-8")
            check(name, process.returncode == 0 and not process.stderr
                  and all(item in process.stdout for item in expected))
            return process.stdout

    a = "0 1 0\n1 1 1\n0 1 0\n"
    b = "1 0 1\n0 1 0\n1 0 1\n"
    zero = "0 0 0\n" * 3
    run("manual_a", "1\n" + a + b + a + "0\n",
        ["A 점수: 5.0, B 점수: 1.0", "판정: A", "3x3 평균 시간:"])
    run("manual_b", "1\n" + a + b + b + "0\n", ["판정: B"])
    run("manual_tie", "1\n" + a + b + zero + "0\n", ["판정: 판정 불가"])
    run("input_validation", "9\n\n1\n0 1\nabc 0 0\nnan 0 0\n\n" + a + b + a + "0\n",
        ["0, 1, 2, 3, 4 중 하나", "한 줄에 숫자 3개", "숫자로 변환할 수 없습니다",
         "유한한 숫자만", "판정: A"])
    output = run("official_data", "2\n0\n", ["총 6 / 통과 3 / 실패 3",
        "size_5_1 동점(UNDECIDED)", "size_13_2 동점(UNDECIDED)",
        "size_25_1 동점(UNDECIDED)", "3x3 /", "5x5 /", "13x13 /", "25x25 /"])
    for mutation in ("shape", "label", "missing_input", "non_numeric"):
        data = copy.deepcopy(original)
        case = data["patterns"]["size_5_1"]
        if mutation == "shape":
            case["input"] = [[0]]
        elif mutation == "label":
            case["expected"] = "unknown"
        elif mutation == "missing_input":
            del case["input"]
        else:
            case["input"][0][0] = "bad"
        run(mutation, "2\n0\n", ["size_5_1: FAIL -", "size_25_2:", "총 6 / 통과 3 / 실패 3"], data)
    run("missing_file", "2\n0\n", ["data.json을 읽을 수 없습니다"], None)
    run("invalid_json", "2\n0\n", ["data.json을 읽을 수 없습니다"], "{")
    run("invalid_schema", "2\n0\n", ["최상위 데이터는 객체"], [])
    run("eof", "", ["입력이 종료되어 마칩니다"])
    check("label_aliases", all(module.normalize_label(x) == y for x, y in
          [("+", "Cross"), ("cross", "Cross"), (" Cross ", "Cross"), ("x", "X"), ("X", "X")]))
    check("epsilon_policy", module.decide(0, 0.5e-9, "A", "B") == "UNDECIDED"
          and module.decide(0, 1e-9, "A", "B") == "B")
    check("mac_values", module.mac([[2, 3]], [[4, 5]]) == 23.0)
    report = {"environment": {"python": sys.version, "platform": platform.platform()},
              "main_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "data_sha256": hashlib.sha256((ROOT / "data.json").read_bytes()).hexdigest(),
              "checks": results, "passed": sum(x["passed"] for x in results),
              "total": len(results)}
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for result in results:
        log = OUT / (result['name'] + '.txt')
        if log.exists():
            log.write_text('\n'.join(line.rstrip() for line in log.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
