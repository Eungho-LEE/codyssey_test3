# Mini NPU Simulator · Codyssey E1-3

2차원 패턴과 필터의 같은 위치 값을 곱해 누적하는 MAC 연산을 Python 반복문으로 구현한 콘솔 프로그램입니다. 사용자 입력과 공식 `data.json` 분석, 라벨 정규화, 동점 판정, 성능 측정과 결과 요약을 제공합니다.

## 실행 환경과 방법

- 요구 환경: Python 3.8 이상, 외부 패키지 설치 없음
- 검증 환경: WSL 2 Ubuntu-26.04, Python 3.14.4, Linux 6.18.54.1-microsoft-standard-WSL2
- 검증일: 2026-11-09

```bash
git clone https://github.com/Eungho-LEE/codyssey_test3.git
cd codyssey_test3
python3 main.py
```

Windows Python에서는 `py -3 main.py`로 실행할 수 있습니다. `data.json`은 `main.py`와 같은 폴더에 둡니다. 파일 경로는 `__file__` 기준이므로 다른 작업 폴더에서 실행해도 같습니다. 실행 중 코드를 고쳤다면 저장한 뒤 메뉴의 `0`으로 종료하고 다시 실행해야 반영됩니다.

| 메뉴 | 입력과 결과 |
| --- | --- |
| `1` | 필터 A 3행 → 필터 B 3행 → 저장 확인 → 패턴 3행 → 점수·판정·3×3 평균 시간 |
| `2` | data.json 로드 → 케이스별 검증·판정 → 3·5·13·25 크기 성능 표 → 총합·실패 원인 |
| `0` | 종료 |

## 모드 1 입력 예시

아래 표의 각 칸을 한 줄씩 입력하고 Enter를 누릅니다. 숫자는 공백으로 구분합니다. `010`이나 `[0, 1, 0]`으로 입력하지 않습니다.

| 대상 | 1행 | 2행 | 3행 |
| --- | --- | --- | --- |
| 필터 A | `0 1 0` | `1 1 1` | `0 1 0` |
| 필터 B | `1 0 1` | `0 1 0` | `1 0 1` |
| 패턴 | `0 1 0` | `1 1 1` | `0 1 0` |

결과는 A=5.0, B=1.0, 판정 A입니다. 시간은 실행마다 달라집니다. 필터는 해당 실행의 메모리에 저장하며 파일로 영구 저장하지 않습니다. 패턴만 X 모양으로 바꾸면 판정 B, 모두 0으로 바꾸면 판정 불가입니다.

## 구현 요약

| 함수 | 역할 |
| --- | --- |
| `mac` | 이중 반복문으로 위치별 곱의 합 계산 |
| `read_grid` | 한 줄 숫자 3개, 숫자 변환, 유한값 검사와 현재 행 재입력 |
| `load_data` | UTF-8/BOM JSON 로드, 최상위 filters·patterns 객체 검사 |
| `normalize_label` | 공백·대소문자 정리 후 `+`·`cross` → Cross, `x` → X |
| `prepare_case` | size_N_idx에서 크기 추출, 필터 선택, 필드·라벨·격자 검증 |
| `decide` | 절대 점수 차이가 `1e-9` 미만이면 UNDECIDED, 그 외 큰 점수 라벨 |
| `average_mac_ms` | 한 필터의 MAC 호출 구간을 10회 측정하고 평균 ms 반환 |
| `benchmark_data` | 3×3 데모와 JSON의 5·13·25 크기별 측정 |
| `print_report` | 전체·통과·실패 수와 실패 케이스별 사유 출력 |

`data.json`은 filters의 size_5·size_13·size_25 필터 묶음과 patterns의 size_N_idx 케이스를 중첩 객체로 보관합니다. 각 케이스는 input 격자와 expected를 가집니다. 두 필터와 패턴이 같은 N×N인지 검사하고, 잘못된 케이스는 FAIL로 기록한 뒤 다음 케이스를 처리합니다. 벡터화·NumPy·pandas를 사용하지 않습니다.

## 결과 리포트

공식 파일을 변경하지 않고 실행한 실제 기록은 [official_data.txt](docs/records/official_data.txt)에 있습니다.

| 케이스 | Cross 점수 | X 점수 | 판정 | expected 정규화 | 결과 |
| --- | --- | --- | --- | --- | --- |
| size_5_1 | 0.9 | 0.9 | UNDECIDED | X | FAIL |
| size_5_2 | 8.9 | 0.1 | Cross | Cross | PASS |
| size_13_1 | 0.3 | 14.7 | X | X | PASS |
| size_13_2 | 7.5 | 7.5 | UNDECIDED | Cross | FAIL |
| size_25_1 | 4.9 | 4.9 | UNDECIDED | X | FAIL |
| size_25_2 | 52.9 | 0.1 | Cross | Cross | PASS |

1. 실제 제공 파일에는 총 6개 케이스가 있으며 통과 3개, 실패 3개입니다.
2. size_5_1은 두 점수가 약 0.9로 같아 UNDECIDED이지만 expected는 X여서 실패합니다.
3. size_13_2는 두 점수가 약 7.5로 같아 UNDECIDED이지만 expected는 Cross여서 실패합니다.
4. size_25_1은 두 점수가 약 4.9로 같아 UNDECIDED이지만 expected는 X여서 실패합니다.
5. 나머지 세 케이스는 큰 점수의 표준 라벨이 expected와 일치해 통과합니다.
6. 이 세 동점 FAIL은 데이터와 비교 정책에 따른 분석 결과이며 프로그램 예외 종료를 뜻하지 않습니다.
7. expected의 `+`와 `x`, 필터 키의 `cross`와 `x`를 정규화해 표기 차이로 인한 오판정을 방지했습니다.
8. 부동소수점의 미세한 차이로 승패가 달라지지 않도록 반올림 전 점수 차이에 절대 허용오차를 적용합니다.
9. `abs(a-b) < 1e-9`가 동점 조건이므로 차이가 정확히 1e-9인 경우는 동점에 포함하지 않습니다.
10. 동점을 임의로 X나 Cross로 바꾸거나 expected를 수정해 통과 수를 늘리지 않았습니다.
11. 한 필터의 N×N MAC은 N²개 위치를 방문하고, 각 위치에서 곱셈과 누적 덧셈을 수행합니다.
12. 따라서 한 필터의 시간 복잡도는 O(N²)이고, 두 필터를 계산해도 상수배 차이여서 O(N²)입니다.
13. 표의 N²는 곱셈·덧셈을 묶은 MAC 위치쌍 수이며, 산술 연산을 각각 세면 대략 2N²입니다.
14. 측정에는 파일 읽기·입력·출력·검증을 포함하지 않고 MAC 함수 호출 구간만 포함합니다.
15. 크기마다 10회 측정한 합계를 10으로 나누고 초를 ms로 변환했습니다.
16. 작은 입력은 함수 호출·시계 측정·OS 스케줄링 영향 때문에 시간 비율이 N² 비율과 정확히 같지는 않습니다.
17. 아래 결과에서는 크기가 커질수록 시간이 증가하지만, 한 번의 측정으로 정확한 성능 배율을 일반화하지 않습니다.
18. 이 프로그램은 CPU에서 실행하는 계산 시뮬레이터이며 실제 NPU의 병렬 처리 성능을 측정하지 않습니다.

### 실제 성능 측정

아래는 검증 실행 한 번에서 나온 값입니다. 한 필터·한 패턴 기준이고, 3×3은 데모 격자, 나머지는 각 크기의 첫 유효 케이스와 Cross 필터를 사용했습니다.

| 크기 | 평균 시간(ms) | MAC 위치쌍 수 N² | 반복 |
| --- | --- | --- | --- |
| 3×3 | 0.000616 | 9 | 10 |
| 5×5 | 0.000875 | 25 | 10 |
| 13×13 | 0.003791 | 169 | 10 |
| 25×25 | 0.012656 | 625 | 10 |

## 검증과 오류 재현

```bash
python3 scripts/verify_submission.py
```

검증 스크립트는 임시 폴더에 프로그램과 데이터를 복사해 실행합니다. 오류 검증용 JSON은 복사본에서만 바꾸며 원본 data.json을 유지합니다. 실행 결과는 docs/records에 저장합니다. 검증 스크립트는 제출물 보조 도구로, 프로그램 실행에는 필요하지 않습니다.

[검증 결과 JSON](docs/records/verification.json): **16개 검사 모두 통과**했습니다. 이는 공식 데이터의 PASS/FAIL 수와 구분되는 프로그램 동작 검증 결과입니다.

| 확인 내용 | 실제 입출력 기록 |
| --- | --- |
| A·B·동점 판정과 평균 시간 | [A](docs/records/manual_a.txt), [B](docs/records/manual_b.txt), [동점](docs/records/manual_tie.txt) |
| 잘못된 메뉴·열 개수·문자·nan·빈 입력 재입력 | [입력 검증](docs/records/input_validation.txt) |
| 공식 6개 분석·성능 표·결과 총합 | [공식 데이터](docs/records/official_data.txt) |
| 격자 크기 불일치 후 다음 케이스 계속 실행 | [크기 오류](docs/records/shape.txt) |
| 알 수 없는 라벨·누락 필드·숫자 아닌 값 | [라벨](docs/records/label.txt), [필드](docs/records/missing_input.txt), [숫자](docs/records/non_numeric.txt) |
| 없는 파일·손상 JSON·최상위 구조 오류 | [파일 없음](docs/records/missing_file.txt), [JSON](docs/records/invalid_json.txt), [구조](docs/records/invalid_schema.txt) |
| 입력 종료 EOF | [종료](docs/records/eof.txt) |

추가로 라벨 별칭, epsilon 안쪽·경계, MAC 손계산 값을 직접 검사했습니다. Ctrl+C 처리 분기는 구현돼 있지만 이번 자동 검사에는 실제 SIGINT 검증을 포함하지 않았습니다.

## 제출 파일과 범위

- 필수: `main.py`, `README.md`
- 재현용 데이터: `data.json`
- 검증 증거: `docs/records/`, 재실행 도구 `scripts/verify_submission.py`
- 학습 기록: `practice_grid.py`, `example_hand.txt`

선택 과제인 1차원 배열 최적화와 일반 N×N 패턴 생성기는 구현하지 않았습니다. 3×3 데모 격자 함수는 임의 크기 생성기가 아닙니다. Git 커밋 수·브랜치 병합은 E1-3 원문에 필수 조건으로 명시돼 있지 않으며, 로컬 제출 정리 시점부터 이력을 남깁니다.
