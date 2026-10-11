"""Measure client round trip and instrumented Catch2 compilation/execution phases."""
import argparse
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.jobe_wrapper import JobeWrapper
from shared.check_catch2 import parse_catch2_report

ANSWER = 'int calculate_sum(int a, int b) { return a + b; }'
TESTS = '''#include <catch2/catch_test_macros.hpp>
int calculate_sum(int, int);
TEST_CASE("sum") { REQUIRE(calculate_sum(2, 3) == 5); }
TEST_CASE("negative") { REQUIRE(calculate_sum(-2, 1) == -1); }
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', default='localhost:4000')
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--output', type=Path, default=Path('artifacts/jobe_cpp_timings.json'))
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    jobe = JobeWrapper(args.server)
    samples = []
    for index in range(args.runs):
        result = jobe.run_test('catch2cpp', TESTS, 'test.cpp',
                               files=JobeWrapper.createFiles({'answer.cpp': ANSWER.encode()}))
        check = parse_catch2_report(result.stdout)
        if not result.success() or not check.wasSuccessful() or check.count != 2:
            raise RuntimeError(f'Benchmark failed: {result!r} {check!r}')
        samples.append({'timings': result.timings, 'stdout': result.stdout,
                        'stderr': result.stderr, 'outcome': result.outcome()[0]})
        cache = 'hit' if result.timings.get('test_cache_hit') else 'miss'
        print(f'Run {index + 1}: {result.timings["total_client_seconds"]:.3f} s (test cache {cache})', flush=True)
    summary = {}
    for key in samples[0]['timings']:
        if not key.endswith('_seconds'):
            continue
        values = [sample['timings'][key] for sample in samples if key in sample['timings']]
        summary[key] = {'median': statistics.median(values), 'min': min(values), 'max': max(values)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'server': args.server, 'language': 'catch2cpp', 'versions': jobe.languages(),
        'summary_seconds': summary, 'samples': samples,
    }, indent=2), encoding='utf-8')
    print('\nPhase                                median ms      min ms      max ms')
    for key, values in summary.items():
        print(f'{key:36} {values["median"] * 1000:10.3f} {values["min"] * 1000:11.3f} {values["max"] * 1000:11.3f}')
    print(f'\nSaved samples and returned XML reports to {args.output}')


if __name__ == '__main__':
    main()
