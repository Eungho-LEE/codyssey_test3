"""Check generated patterns, result equivalence, and real CLI performance."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/records'
spec = importlib.util.spec_from_file_location('npu_submission', ROOT / 'main.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks, sessions, benchmarks = [], [], []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'name': name, 'passed': True})


for n in (1, 2, 3, 4, 5, 13, 25, 101):
    cross, x_grid = module.generate_patterns(n)
    check(f'shape and binary values {n}', all(len(g) == n and all(len(r) == n and set(r) <= {0, 1} for r in g) for g in (cross, x_grid)))
    check(f'Cross axes {n}', all(cross[r][c] == int(r == n // 2 or c == n // 2) for r in range(n) for c in range(n)))
    check(f'X diagonals {n}', all(x_grid[r][c] == int(r == c or r + c == n - 1) for r in range(n) for c in range(n)))
    check(f'flat length and scores {n}', len(module.flatten(cross)) == n * n and module.mac(cross, x_grid) == module.mac_flat(module.flatten(cross), module.flatten(x_grid)))
check('3x3 matches original examples', module.generate_patterns(3) == module.demo_grids())
for invalid in (0, -1, 102, 1.5, True, '3'):
    try:
        module.generate_patterns(invalid)
    except ValueError:
        check('reject generator size ' + repr(invalid), True)
    else:
        raise AssertionError(invalid)
rng = random.Random(20261110)
for n in (3, 5, 13, 25):
    pattern = [[rng.uniform(-3, 3) for _ in range(n)] for _ in range(n)]
    weights = [[rng.uniform(-3, 3) for _ in range(n)] for _ in range(n)]
    check(f'nonbinary numeric equivalence {n}', module.mac(pattern, weights) == module.mac_flat(module.flatten(pattern), module.flatten(weights)))
    # Use exactly the same generated input for both layouts in every round.
    cross, x_grid = module.generate_patterns(n)
    result = module.compare_layouts(cross, x_grid, repeats=1000, rounds=5)
    check(f'benchmark valid {n}', result['two_dimensional_ms'] > 0 and result['flat_ms'] > 0 and result['score'] == result['flat_score'])
    benchmarks.append(result)
for name, action in [
    ('flat length mismatch', lambda: module.mac_flat([1], [])),
    ('invalid repetition count', lambda: module.compare_layouts([[1]], [[1]], repeats=0)),
    ('invalid shape', lambda: module.compare_layouts([[1]], [[1, 2]])),
    ('nonfinite value', lambda: module.compare_layouts([[float('nan')]], [[1]])),
]:
    try:
        action()
    except ValueError:
        check(name, True)
    else:
        raise AssertionError(name)
with tempfile.TemporaryDirectory(prefix='npu-bonus-') as temporary:
    folder = Path(temporary)
    shutil.copy2(ROOT / 'main.py', folder / 'main.py')
    shutil.copy2(ROOT / 'data.json', folder / 'data.json')
    for name, inputs, expected in [
        ('generate_cross', '3\n0\nabc\n102\n3\n9\n1\n0\n', ['크기는 1~101', '1 또는 2', '판정: A', '결과 일치: 5.0 == 5.0']),
        ('generate_x', '3\n5\n2\n0\n', ['판정: B', '5x5 평균 시간', '결과 일치']),
        ('even_size', '3\n4\n1\n0\n', ['4x4 평균 시간', '결과 일치']),
        ('degenerate_tie', '3\n1\n1\n0\n', ['판정: 판정 불가', '1x1 평균 시간']),
        ('compare_layouts', '4\n0\n', ['동일 입력 3x3', '동일 입력 25x25', '각 1000회 × 5라운드', '1D 변환']),
        ('original_json', '2\n0\n', ['총 6 / 통과 3 / 실패 3']),
        ('generator_eof', '3\n', ['입력이 종료되어 마칩니다']),
    ]:
        process = subprocess.run([sys.executable, str(folder / 'main.py')], input=inputs,
                                 text=True, capture_output=True, cwd=folder, timeout=20)
        check(name, process.returncode == 0 and not process.stderr and all(text in process.stdout for text in expected))
        sessions.append({'name': name, 'stdin': inputs, 'stdout': process.stdout,
                         'stderr': process.stderr, 'returncode': process.returncode})
OUT.mkdir(parents=True, exist_ok=True)
report = {'date': '2026-11-10', 'python': sys.version, 'platform': platform.platform(),
          'main_sha256': hashlib.sha256((ROOT / 'main.py').read_bytes()).hexdigest(),
          'passed': len(checks), 'checks': checks, 'benchmarks': benchmarks, 'sessions': sessions}
(OUT / 'bonus-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'bonus-cli.txt').write_text('\n\n'.join(
    '$ python3 main.py\n[STDIN]\n' + s['stdin'] + '\n[STDOUT]\n' + s['stdout']
    + '\n[STDERR]\n' + (s['stderr'] or '(none)') + f"\n[exit={s['returncode']}]" for s in sessions) + '\n', encoding='utf-8')
rows = ['# 2D·1D MAC 실제 성능 비교', '', '동일 입력·반복 수, 각 1000회 × 5라운드의 호출당 평균 시간 중앙값. 변환은 측정 구간 밖에서 한 번만 수행했다.', '',
        '| N | 2D ms | 1D ms | 2D/1D | 변환 1회 ms |', '| --- | --- | --- | --- | --- |']
for r in benchmarks:
    rows.append(f"| {r['size']} | {r['two_dimensional_ms']:.6f} | {r['flat_ms']:.6f} | {r['speedup']:.3f} | {r['conversion_ms']:.6f} |")
rows += ['', '속도비가 1보다 크면 이번 측정에서 1D가 빨랐다는 뜻이다. 두 구현 모두 O(N²)이고, Python 객체를 담는 리스트이므로 연속 숫자 메모리나 실제 NPU 메모리 최적화를 증명하지는 않는다. 단발 실행에서는 변환 비용도 포함해 판단해야 하며 실행 환경에 따라 결과가 달라진다.', '']
(OUT / 'bonus-performance.md').write_text('\n'.join(rows), encoding='utf-8')
log = OUT / 'bonus-cli.txt'
log.write_text('\n'.join(line.rstrip() for line in log.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
print(json.dumps({'passed': len(checks), 'sessions': len(sessions), 'benchmarks': benchmarks}))
