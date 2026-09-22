"""Small local mistake journal. No automatic upload and no fixed study calendar."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

STRATEGIES = {
    'concept': '先用自己的话解释概念和适用条件，再做一道辨析题。',
    'method': '先指出题目触发哪个方法，再独立完成一道同结构题。',
    'calculation': '重做首次出错的一步，写出中间过程，再做一道短计算。',
    'reading': '圈出限制条件与结论，解释关键词后重新作答。',
    'memory': '合上答案回忆关键结论，再用一道应用题检验。',
    'grammar': '标出主干和从句边界，再拆解一句相同结构的新句。',
    'vocabulary': '解释当前语境中的词义和搭配，再造一句新句。',
    'writing': '先自行修改一个影响表达的问题，再迁移到一个新句。',
    'unknown': '错因还未确认：先解释你当时的第一步，不急于增加练习量。',
}


def add(records, topic, error_type, evidence, source=''):
    if not topic.strip() or not evidence.strip():
        raise ValueError('Topic and observed evidence are required')
    if error_type not in STRATEGIES:
        raise ValueError('Unknown error type')
    record = dict(id=uuid.uuid4().hex[:12], topic=topic.strip(), error_type=error_type,
                  evidence=evidence.strip(), source=source, created_at=datetime.now(timezone.utc).isoformat(),
                  attempts=[], status='needs-check')
    records.append(record)
    return record


def review(records, identity, result, note=''):
    if result not in ('independent-correct','hinted-correct','incorrect'):
        raise ValueError('Invalid result')
    item = next((r for r in records if r['id'] == identity), None)
    if item is None:
        raise ValueError('Unknown mistake ID')
    item['attempts'].append(dict(result=result, note=note, at=datetime.now(timezone.utc).isoformat()))
    recent = [a['result'] for a in item['attempts'][-2:]]
    item['status'] = 'provisionally-improved' if recent == ['independent-correct']*2 else 'needs-check'
    return item


def feedback(records, topic):
    items = [r for r in records if r['topic'] == topic]
    pending = [r for r in items if r['status'] != 'provisionally-improved']
    if not items:
        return dict(topic=topic, message='还没有该知识点的已观察错题，不推断薄弱程度。', actions=[])
    focus = pending[-1] if pending else items[-1]
    return dict(topic=topic, observed_mistakes=len(items), pending=len(pending),
                evidence=focus['evidence'], error_type=focus['error_type'],
                actions=[STRATEGIES[focus['error_type']],
                         '默认只安排 1–3 道针对性题目；先核验题源和答案，再反馈下一步。'],
                note='两次独立答对只作为临时改善信号，不表示已永久掌握；不自动生成日程。')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--journal',type=Path,default=Path(__file__).resolve().parents[1]/'private/mistakes.json')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('add');a.add_argument('--topic',required=True);a.add_argument('--error-type',choices=STRATEGIES,default='unknown');a.add_argument('--evidence',required=True);a.add_argument('--source',default='')
    a=sub.add_parser('review');a.add_argument('id');a.add_argument('--result',choices=['independent-correct','hinted-correct','incorrect'],required=True);a.add_argument('--note',default='')
    a=sub.add_parser('feedback');a.add_argument('topic')
    sub.add_parser('list')
    args=p.parse_args()
    records=json.loads(args.journal.read_text(encoding='utf-8')) if args.journal.exists() else []
    if args.command=='add': result=add(records,args.topic,args.error_type,args.evidence,args.source)
    elif args.command=='review':result=review(records,args.id,args.result,args.note)
    elif args.command=='feedback':result=feedback(records,args.topic)
    else:result=records
    if args.command in ('add','review'):
        args.journal.parent.mkdir(parents=True,exist_ok=True)
        temp=args.journal.with_suffix('.tmp')
        temp.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temp.replace(args.journal)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
