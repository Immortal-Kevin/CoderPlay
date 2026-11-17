"""Opt-in evaluation using the installed local Vulkan model."""
import argparse
import json
from pathlib import Path

import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='运行本地模型评测')
    parser.add_argument('--limit',type=int,default=3,choices=range(1,33),metavar='1..32')
    args = parser.parse_args()
    if not args.run:
        parser.error('本地评测需要明确指定 --run')
    cases = json.loads(Path(__file__).with_name('cases.json').read_text(encoding='utf-8'))
    results = []
    for case in cases[:args.limit]:
        try:
            output = app.translate(case | dict(record_history=False, use_examples=False))
            results.append(dict(id=case['id'],generated=True,expected=case['expected'],
                                forbidden=case['forbidden'],output=output))
        except ValueError as e:
            results.append(dict(id=case['id'],generated=False,error=str(e)))
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return 0 if all(x['generated'] for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
