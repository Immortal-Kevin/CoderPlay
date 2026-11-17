"""Opt-in evaluation using the installed local Vulkan model."""
import argparse
import json
from pathlib import Path

import app
import local_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='运行本地模型评测')
    parser.add_argument('--limit',type=int,default=3,choices=range(1,33),metavar='1..32')
    args = parser.parse_args()
    if not args.run:
        parser.error('本地评测需要明确指定 --run')
    cases = json.loads(Path(__file__).with_name('cases.json').read_text(encoding='utf-8'))
    prompt = app.REVIEW + ' 同时用 expected 和 forbidden 作语义验收条件；reference 只作参考。'
    results = []
    for case in cases[:args.limit]:
        try:
            output = app.translate(case | dict(record_history=False, use_examples=False))
            review = app.structured(prompt,case | output)
            passed = review.get('pass') is True and review.get('issues') == []
            results.append(dict(id=case['id'],pass_=passed,expected=case['expected'],
                                forbidden=case['forbidden'],output=output,review=review))
        except ValueError as e:
            results.append(dict(id=case['id'],pass_=False,error=str(e)))
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return 0 if all(x['pass_'] for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
