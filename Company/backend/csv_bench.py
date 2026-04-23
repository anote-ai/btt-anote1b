import os
import csv
import json
import re
from typing import Dict, Any, List, Tuple, Optional

import requests


def csv_root_dir() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # Repo layout: backend/../frontend/public/benchmark_csvs
    return os.path.abspath(os.path.join(here, '..', 'frontend', 'public', 'benchmark_csvs'))


def list_csv_datasets() -> List[Dict[str, Any]]:
    root = csv_root_dir()
    if not os.path.isdir(root):
        return []
    items: List[Dict[str, Any]] = []
    for name in os.listdir(root):
        if not name.lower().endswith('.csv'):
            continue
        path = os.path.join(root, name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, [])
        except Exception:
            header = []
        task = infer_task_type(header)
        items.append({
            'filename': name,
            'path': path,
            'task_type': task,
            'columns': header,
        })
    return items


def infer_task_type(header: List[str]) -> str:
    cols = {c.strip().lower() for c in header}
    if {'optiona', 'optionb', 'optionc', 'optiond'}.issubset(cols) and ('correct answer' in cols or 'correct_answer' in cols or 'answer' in cols):
        return 'multiple_choice'
    if 'options' in cols and ('correct answer' in cols or 'answer' in cols or 'label' in cols):
        return 'multiple_choice'
    if 'label' in cols:
        return 'text_classification'
    if 'answer' in cols and 'question' in cols:
        return 'qa'
    return 'unknown'


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def score_accuracy(golds: List[str], preds: List[str]) -> float:
    if not golds:
        return 0.0
    ok = 0
    for g, p in zip(golds, preds):
        if _norm_text(str(g)) == _norm_text(str(p)):
            ok += 1
    return ok / len(golds)


def _f1_tokens(a_gold: str, a_pred: str) -> float:
    gold_t = _norm_text(a_gold).split()
    pred_t = _norm_text(a_pred).split()
    if not gold_t and not pred_t:
        return 1.0
    if not gold_t or not pred_t:
        return 0.0
    common = 0
    counts = {}
    for t in gold_t:
        counts[t] = counts.get(t, 0) + 1
    for t in pred_t:
        if counts.get(t, 0) > 0:
            common += 1
            counts[t] -= 1
    if common == 0:
        return 0.0
    prec = common / len(pred_t)
    rec = common / len(gold_t)
    return 2 * prec * rec / (prec + rec)


def score_qa(golds: List[str], preds: List[str]) -> Dict[str, float]:
    if not golds:
        return {'em': 0.0, 'f1': 0.0}
    em = sum(1 for g, p in zip(golds, preds) if _norm_text(g) == _norm_text(p)) / len(golds)
    f1 = sum(_f1_tokens(g, p) for g, p in zip(golds, preds)) / len(golds)
    return {'em': em, 'f1': f1}


def parse_mc_answer(text: str, allowed: str = "ABCDE") -> Optional[str]:
    if not text:
        return None
    m = re.search(r"([A-E])", text.upper())
    if m and m.group(1) in allowed:
        return m.group(1)
    return None


def build_prompt(task: str, row: Dict[str, Any], header: List[str]) -> str:
    if task == 'multiple_choice':
        # Handle both OptionA.. and stringified list in 'options'
        if all(k in row for k in ('OptionA', 'OptionB', 'OptionC', 'OptionD')):
            question = row.get('Question') or row.get('question') or ''
            opts = [row.get('OptionA', ''), row.get('OptionB', ''), row.get('OptionC', ''), row.get('OptionD', '')]
            # Some have OptionE
            if 'OptionE' in row:
                opts.append(row.get('OptionE', ''))
        else:
            question = row.get('question') or row.get('Question') or ''
            try:
                opts = json.loads(row.get('options') or '[]')
            except Exception:
                opts = []
        lines = [
            "You are a multiple-choice solver. Answer with a single letter only.",
            f"Question: {question}",
            "Options:",
        ]
        letters = ['A', 'B', 'C', 'D', 'E']
        for i, o in enumerate(opts[:5]):
            lines.append(f"{letters[i]}) {o}")
        lines.append("Respond with only the letter (A-E).")
        return "\n".join(lines)
    elif task == 'text_classification':
        text = row.get('text') or row.get('sample') or row.get('tweet') or ''
        return (
            "Classify the following text. Respond with only the label value (integer or string) that best fits.\n"
            f"Text: {text}\nLabel:"
        )
    elif task == 'qa':
        question = row.get('question') or row.get('Question') or ''
        context = row.get('context') or row.get('Context')
        if context:
            return f"Answer the question based on the context. Be concise.\nContext: {context}\nQuestion: {question}\nAnswer:"
        return f"Answer the question concisely.\nQuestion: {question}\nAnswer:"
    else:
        # Fallback
        return "Return OK"


# -------------------
# Model providers
# -------------------
def call_model(provider: str, model_name: str, prompt: str, base_url: Optional[str] = None, api_key: Optional[str] = None, system: Optional[str] = None, fn: Optional[str] = None) -> str:
    provider = (provider or '').lower()
    if provider == 'echo':
        # Useful for dry-runs
        return prompt[:200]
    if provider in ('py', 'function', 'models'):
        # Call a Python function in backend/models.py
        try:
            import importlib
            m = importlib.import_module('models')
            fn_name = fn or model_name
            if not hasattr(m, fn_name):
                return f"ERROR: models.{fn_name} not found"
            func = getattr(m, fn_name)
            return str(func(prompt))
        except Exception as e:
            return f"ERROR: {e}"
    if provider == 'ollama':
        url = base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        try:
            resp = requests.post(url.rstrip('/') + '/api/generate', json={
                'model': model_name,
                'prompt': prompt,
                'stream': False,
            }, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get('response', '')).strip()
        except Exception as e:
            return f"ERROR: {e}"
    # Default: OpenAI-compatible chat
    url = (base_url or os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com').rstrip('/') + '/v1/chat/completions'
    key = api_key or os.getenv('OPENAI_API_KEY')
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    payload = {
        'model': model_name,
        'messages': ([{'role': 'system', 'content': system}] if system else []) + [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"ERROR: {e}"


def read_rows(path: str, limit: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    header: List[str] = []
    with open(path, 'r', encoding='utf-8') as f:
        # Sniff dialect lightly to handle CRLF
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        for i, row in enumerate(reader):
            rows.append(row)
            if i + 1 >= limit:
                break
    return rows, header


def evaluate_csv_dataset(path: str, task: str, models: List[Dict[str, Any]], sample_size: int = 50) -> Dict[str, Any]:
    rows, header = read_rows(path, sample_size)
    if not rows:
        return {'dataset': os.path.basename(path), 'task_type': task, 'results': {}, 'count': 0}
    golds: List[str] = []
    # Derive gold labels/answers for supported tasks
    if task == 'multiple_choice':
        # Expect a column for correct answer: 'Correct Answer' or 'answer'
        ans_key = 'Correct Answer' if 'Correct Answer' in header else ('answer' if 'answer' in header else None)
        if not ans_key:
            return {'dataset': os.path.basename(path), 'task_type': task, 'results': {}, 'count': len(rows)}
        for r in rows:
            golds.append(str(r.get(ans_key, '')).strip().upper()[:1])
    elif task == 'text_classification':
        # Expect 'label'
        for r in rows:
            golds.append(str(r.get('label', '')).strip())
    elif task == 'qa':
        for r in rows:
            golds.append(str(r.get('answer', '')).strip())
    else:
        # Unknown/unsupported
        return {'dataset': os.path.basename(path), 'task_type': task, 'results': {}, 'count': len(rows)}

    results: Dict[str, Any] = {}
    for m in models:
        name = m.get('name') or m.get('model') or 'model'
        provider = m.get('provider', 'openai')
        model_name = m.get('model') or name
        base_url = m.get('base_url')
        api_key = m.get('api_key')
        preds: List[str] = []
        for r in rows:
            prompt = build_prompt(task, r, header)
            out = call_model(provider, model_name, prompt, base_url=base_url, api_key=api_key, fn=m.get('fn'))
            if task == 'multiple_choice':
                pred = parse_mc_answer(out) or ''
            elif task == 'text_classification':
                # Extract a simple token (number/word)
                mnum = re.search(r"[-+]?[0-9]+", out)
                pred = mnum.group(0) if mnum else out.strip().split()[0] if out.strip() else ''
            else:  # qa
                pred = out.strip()
            preds.append(pred)
        if task == 'multiple_choice' or task == 'text_classification':
            score = score_accuracy(golds, preds)
            results[name] = {'metric': 'accuracy', 'score': float(score)}
        else:
            s = score_qa(golds, preds)
            results[name] = {'metric': 'f1', 'score': float(s['f1']), 'em': float(s['em'])}

    return {
        'dataset': os.path.basename(path),
        'task_type': task,
        'results': results,
        'count': len(rows),
    }


def run_benchmarks(models: List[Dict[str, Any]], datasets: Optional[List[str]] = None, sample_size: int = 25) -> Dict[str, Any]:
    items = list_csv_datasets()
    selected = [it for it in items if (not datasets or it['filename'] in datasets)]
    summary: Dict[str, Any] = {'runs': []}
    for it in selected:
        if it['task_type'] in ('unknown',):
            continue
        res = evaluate_csv_dataset(it['path'], it['task_type'], models=models, sample_size=sample_size)
        summary['runs'].append(res)
    return summary
