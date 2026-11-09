import math


import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent / "data.json"


import re


from time import perf_counter


EPSILON = 1e-9


def demo_grids():
    cross = [[0,1,0],[1,1,1],[0,1,0]]
    x_grid = [[1,0,1],[0,1,0],[1,0,1]]
    return cross, x_grid


def mac(pattern, filter_grid):
    total = 0.0
    for row in range(len(pattern)):
        for column in range(len(pattern[row])):
            total += pattern[row][column] * filter_grid[row][column]
    return total


def read_grid(name, n=3):
    rows = []
    print(f"{name}: {n}줄, 각 줄에 숫자 {n}개")
    while len(rows) < n:
        raw = input(f"{len(rows) + 1}행: ").strip().split()
        if len(raw) != n:
            print(f"한 줄에 숫자 {n}개를 입력하세요.")
            continue
        try:
            row = [float(token) for token in raw]
        except ValueError:
            print("숫자로 변환할 수 없습니다.")
            continue
        if not all(math.isfinite(value) for value in row):
            print("유한한 숫자만 입력하세요.")
            continue
        rows.append(row)
    return rows


def decide(score_a, score_b, label_a, label_b):
    if abs(score_a - score_b) < EPSILON:
        return "UNDECIDED"
    return label_a if score_a > score_b else label_b


def load_data():
    with DATA_PATH.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("최상위 데이터는 객체여야 합니다.")
    if not isinstance(data.get("filters"), dict):
        raise ValueError("filters는 객체여야 합니다.")
    if not isinstance(data.get("patterns"), dict):
        raise ValueError("patterns는 객체여야 합니다.")
    return data


def normalize_label(value):
    if not isinstance(value, str):
        raise ValueError("라벨은 문자열이어야 합니다.")
    aliases = {"+": "Cross", "cross": "Cross", "x": "X"}
    key = value.strip().lower()
    if key not in aliases:
        raise ValueError(f"지원하지 않는 라벨: {value}")
    return aliases[key]


def parse_size(case_id):
    match = re.fullmatch(r"size_(\d+)_(\d+)", case_id)
    if match is None:
        raise ValueError("패턴 키는 size_N_idx 형식이어야 합니다.")
    n = int(match.group(1))
    if n not in (5, 13, 25):
        raise ValueError(f"지원하지 않는 데이터 크기: {n}")
    return n


def select_filters(data, n):
    raw = data["filters"][f"size_{n}"]
    if not isinstance(raw, dict):
        raise ValueError("필터 묶음은 객체여야 합니다.")
    normalized = {}
    for label, grid in raw.items():
        label = normalize_label(label)
        if label in normalized:
            raise ValueError(f"중복된 표준 필터 라벨: {label}")
        normalized[label] = grid
    if not all(label in normalized for label in ("Cross", "X")):
        raise ValueError("Cross와 X 필터가 모두 필요합니다.")
    return normalized


def validate_grid(grid, n):
    if not isinstance(grid, list) or len(grid) != n:
        raise ValueError(f"행 수가 {n}이 아닙니다.")
    for row in grid:
        if not isinstance(row, list) or len(row) != n:
            raise ValueError(f"열 수가 {n}이 아닙니다.")
        for value in row:
            if type(value) not in (int, float):
                raise ValueError("격자는 숫자만 포함해야 합니다.")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                raise ValueError("숫자가 처리 가능한 범위를 벗어났습니다.")
            if not finite:
                raise ValueError("격자 값은 유한해야 합니다.")


def prepare_case(data, case_id, case):
    if not isinstance(case_id, str) or not isinstance(case, dict):
        raise ValueError("케이스 이름 또는 데이터 구조가 잘못됐습니다.")
    n = parse_size(case_id)
    filters = select_filters(data, n)
    pattern = case["input"]
    expected = normalize_label(case["expected"])
    for grid in (pattern, filters["Cross"], filters["X"]):
        validate_grid(grid, n)
    return n, pattern, filters, expected


def analyze_cases(data):
    results = []
    for case_id, case in data["patterns"].items():
        try:
            n, pattern, filters, expected = prepare_case(data, case_id, case)
            cross_score = mac(pattern, filters["Cross"])
            x_score = mac(pattern, filters["X"])
            if not all(math.isfinite(score) for score in (cross_score, x_score)):
                raise ValueError("계산 결과가 유한한 범위를 벗어났습니다.")
            predicted = decide(cross_score, x_score, "Cross", "X")
            status = "PASS" if predicted == expected else "FAIL"
            reason = "" if status == "PASS" else (
                "동점(UNDECIDED)" if predicted == "UNDECIDED" else "expected와 판정 불일치"
            )
            result = {"case_id": case_id, "cross": cross_score, "x": x_score,
                      "predicted": predicted, "expected": expected,
                      "status": status, "reason": reason}
            print(f"{case_id}: Cross={cross_score:.12g}, X={x_score:.12g}, "
                  f"판정={predicted}, expected={expected}, {status}")
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            result = {"case_id": case_id, "status": "FAIL", "reason": str(error)}
            print(f"{case_id}: FAIL - {error}")
        results.append(result)
    return results


def average_mac_ms(pattern, filter_grid, repeats=10):
    if repeats < 10:
        raise ValueError("최소 10회 측정해야 합니다.")
    elapsed = 0.0
    for _ in range(repeats):
        start = perf_counter()
        mac(pattern, filter_grid)
        elapsed += perf_counter() - start
    return elapsed / repeats * 1000


def benchmark_data(data):
    print("크기 / 한 필터 평균 시간(ms) / MAC 위치쌍 수 / 반복")
    cross, x_grid = demo_grids()
    for n in (3, 5, 13, 25):
        try:
            if n == 3:
                pattern, filter_grid = cross, x_grid
            else:
                selected = None
                for case_id, case in data["patterns"].items():
                    try:
                        size, pattern, filters, expected = prepare_case(data, case_id, case)
                        if size == n:
                            selected = (pattern, filters["Cross"])
                            break
                    except (ValueError, KeyError, TypeError, OverflowError):
                        continue
                if selected is None:
                    raise ValueError("측정 가능한 입력·필터가 없습니다.")
                pattern, filter_grid = selected
            elapsed_ms = average_mac_ms(pattern, filter_grid, repeats=10)
            print(f"{n}x{n} / {elapsed_ms:.6f} / {n*n} / 10")
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            print(f"{n}x{n} / 측정 불가: {error} / {n*n} / -")


def print_report(results):
    total = len(results)
    passed = sum(1 for result in results if result["status"] == "PASS")
    failed = total - passed
    print(f"총 {total} / 통과 {passed} / 실패 {failed}")
    for result in results:
        if result["status"] == "FAIL":
            print(result["case_id"], result["reason"])


def run_manual():
    a = read_grid("필터 A")
    b = read_grid("필터 B")
    print("필터를 메모리에 저장했습니다.")
    pattern = read_grid("패턴")
    score_a = mac(pattern, a)
    score_b = mac(pattern, b)
    if not all(math.isfinite(value) for value in (score_a, score_b)):
        print("계산 결과가 유한하지 않습니다. 더 작은 값을 사용하세요.")
        return
    print(f"A 점수: {score_a}, B 점수: {score_b}")
    result = decide(score_a, score_b, "A", "B")
    print("판정:", "판정 불가" if result == "UNDECIDED" else result)
    print(f"3x3 평균 시간: {average_mac_ms(pattern, a, 10):.6f} ms / 9 MAC 위치쌍 / 10회")


def run_json():
    try:
        data = load_data()
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"data.json을 읽을 수 없습니다: {error}")
        return
    results = analyze_cases(data)
    benchmark_data(data)
    print_report(results)


def main():
    try:
        while True:
            choice = input("1. 사용자 입력 / 2. data.json / 0. 종료: ").strip()
            if choice == "0":
                return
            elif choice == "1":
                run_manual()
            elif choice == "2":
                run_json()
            else:
                print("0, 1, 2 중 하나를 입력하세요.")
    except (KeyboardInterrupt, EOFError):
        print("\n입력이 종료되어 마칩니다.")


if __name__ == "__main__":
    main()