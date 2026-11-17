"""Run repeated, opt-in intensity evaluation and emit rows for human review."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--send', action='store_true', help='向已配置的模型发送测试数据')
    parser.add_argument('--case-count', type=int, choices=range(1, 16), default=1)
    parser.add_argument('--repeats', type=int, choices=range(2, 11), default=3)
    args = parser.parse_args()
    if not args.send:
        parser.error('网络评测需要指定 --send。')

    folder = Path(__file__).parent
    fixtures = {r['id']: r for r in json.loads((folder / 'cases.json').read_text(encoding='utf-8'))}
    matrix = json.loads((folder / 'intensity_cases.json').read_text(encoding='utf-8'))
    cfg = app.clean_config(app.config()) | dict(history=False, share_examples=False)
    rubric = (app.REVIEW + ' 使用 expected 与 forbidden 检查语义；reference 仅供参考，'
              '不要求同一参考句符合所有强度。')
    failed = False
    with patch.object(app, 'config', return_value=cfg):
        for row in matrix[:args.case_count * 6]:
            case = fixtures[row['case_id']]
            case = case | {'options': case['options'] | {'intensity': row['intensity']}}
            for repeat in range(1, args.repeats + 1):
                report = row | dict(repeat=repeat, model=cfg['model'],
                                    temperature=cfg['temperature'], **case)
                try:
                    result = app.translate(case)
                    review = app.structured(cfg, rubric, case | result)
                    passed = review.get('pass') is True and review.get('issues') == []
                    report.update(output=result, review=review, passed=passed)
                    failed |= not passed
                except ValueError as exc:
                    report.update(error=str(exc), passed=False)
                    failed = True
                print(json.dumps(report, ensure_ascii=False), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
