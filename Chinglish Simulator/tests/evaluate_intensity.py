"""Opt-in evaluation using the installed local Vulkan model."""
import argparse
import json
from pathlib import Path

import app
import local_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='运行本地模型评测')
    parser.add_argument('--case-count', type=int, choices=range(1, 16), default=1)
    parser.add_argument('--repeats', type=int, choices=range(2, 11), default=3)
    args = parser.parse_args()
    if not args.run:
        parser.error('本地评测需要指定 --run。')

    folder = Path(__file__).parent
    fixtures = {r['id']: r for r in json.loads((folder / 'cases.json').read_text(encoding='utf-8'))}
    matrix = json.loads((folder / 'intensity_cases.json').read_text(encoding='utf-8'))
    failed = False
    for row in matrix[:args.case_count * 6]:
        case = fixtures[row['case_id']]
        case = case | {'options': case['options'] | {'intensity': row['intensity']}}
        for repeat in range(1, args.repeats + 1):
            report = row | dict(repeat=repeat, model=local_model.MODEL_NAME,
                                temperature=local_model.TEMPERATURE, **case)
            try:
                result = app.translate(case | dict(record_history=False, use_examples=False))
                report.update(output=result, generated=True)
            except ValueError as exc:
                report.update(error=str(exc), generated=False)
                failed = True
            print(json.dumps(report, ensure_ascii=False), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
