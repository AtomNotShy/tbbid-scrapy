from ltp import LTP
import re

ltp = LTP()

def split_sentences(text):
    return [s.strip() for s in re.split(r'[。！？；]', text) if s.strip()]

def extract_project_info(text):
    funding = None
    personnel = []
    entities = []

    for sent in split_sentences(text):
        # 一次性拿到分词和NER
        output = ltp.pipeline([sent], tasks=['cws', 'ner'])
        words = output['cws'][0]
        ner_spans = output['ner'][0]

        # 资金来源
        if '资金来源' in sent:
            m = re.search(r'资金来源[：:]\s*([^，。；]+)', sent)
            if m:
                funding = m.group(1).strip()

        # 人员要求
        if any(k in sent for k in ['资格', '证书', '具备', '配备']):
            personnel.append(sent)

        # 组织/地点实体
        for ent in ner_spans:
            # 处理不同长度的元组
            if len(ent) == 3:
                st, ed, label = ent
            elif len(ent) == 4:
                # 跳过可能的 sentence_id
                _, st, ed, label = ent
            else:
                continue
            if label in ('ORG', 'LOC'):
                entities.append((''.join(words[st:ed+1]), label))

    return {'funding': funding, 'personnel': personnel, 'entities': entities}

if __name__ == '__main__':
    with open('test.html', encoding='utf-8') as f:
        text = f.read()
    info = extract_project_info(text)
    print("资金来源:", info['funding'])
    print("人员要求:")
    for p in info['personnel']:
        print(" -", p)
    print("组织/地点实体:")
    for ent, lbl in info['entities']:
        print(f" * {ent} ({lbl})")
