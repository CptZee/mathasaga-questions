# load_problems.py
import json
import os
import re
from typing import Optional

# --- Try OpenAI ---
USE_OPENAI = os.getenv("OPENAI_API_KEY") is not None
if USE_OPENAI:
    from openai import OpenAI
    client = OpenAI()
else:
    import mathgenerator


# --- Prompt template for ChatGPT ---
PROMPT_TEMPLATE = """
You are a math problem generator for a Grade 3 educational game.
Generate {count} unique math word problems for {operation}, where {operation} is one of: Addition, Substraction, Multiplication, Division.

Each problem must:
- Be written as a short word problem suitable for Grade 3 students.
- Have a single correct numeric answer.
- Use simple, everyday contexts (candies, apples, toys, kids, etc.).
- Keep numbers reasonable (within 1–100).
- No fractions, decimals, or negative results.
- Output in strict JSON with the format:

{
  "Questions": [
    {
      "Text": "<word problem text>",
      "Operation": "{operation}",
      "status": "Available",
      "Answer": <numeric answer>
    }
  ]
}
"""

# --- OpenAI-based generator ---
def fetch_questions_openai(operation: str, count: int = 5):
    prompt = PROMPT_TEMPLATE.format(count=count, operation=operation)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    content = response.choices[0].message.content

    try:
        data = json.loads(content)
        return data.get("Questions", [])
    except Exception as e:
        print("⚠ Failed to parse response from OpenAI:", e)
        print("Raw response was:", content)
        return []


# --- Mathgenerator fallback ---
OP_FUNCS = {
    "Addition": mathgenerator.addition if not USE_OPENAI else None,
    "Substraction": mathgenerator.subtraction if not USE_OPENAI else None,
    "Multiplication": mathgenerator.multiplication if not USE_OPENAI else None,
    "Division": mathgenerator.division if not USE_OPENAI else None,
}

def sanitize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = s.replace("$", "")
    s = re.sub(r'\\frac\{(-?\d+)\}\{(-?\d+)\}', r'\1/\2', s)
    s = s.replace(r'\times', '×').replace(r'\\times', '×')
    s = s.replace(r'\div', '÷').replace(r'\\div', '÷')
    s = s.replace(r'\cdot', '×')
    s = re.sub(r'\\[^\s]*', '', s)
    s = s.rstrip().rstrip('=').strip()
    s = s.replace('+', ' + ').replace('-', ' - ').replace('×', ' × ').replace('÷', ' ÷ ')
    return re.sub(r'\s+', ' ', s).strip()

def sanitize_answer(a: str) -> Optional[float]:
    if a is None:
        return None
    s = str(a).strip().replace("$", "").replace(r'\,', '').replace('\u2212', '-')
    s_plain = s.replace(',', '')
    if re.fullmatch(r'[-+]?\d+(\.\d+)?', s_plain):
        return float(s_plain)
    m = re.fullmatch(r'(-?\d+)\s*/\s*(\d+)', s)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return None if den == 0 else num / den
    return None


# --- Generate wrapper ---
def generate_questions(per_op: int = 20):
    operations = ["Addition", "Substraction", "Multiplication", "Division"]
    all_questions = []

    if USE_OPENAI:
        print("🔑 Using OpenAI API for worded problems...")
        for op in operations:
            qs = fetch_questions_openai(op, per_op)
            all_questions.extend(qs)
    else:
        print("🧮 No API key found. Using mathgenerator fallback...")
        skipped = 0
        for op, func in OP_FUNCS.items():
            for _ in range(per_op):
                try:
                    q_text, q_answer = func()
                    txt = sanitize_text(q_text)
                    ans = sanitize_answer(q_answer)
                    if ans is None:
                        skipped += 1
                        continue
                    all_questions.append({
                        "Text": txt,
                        "Operation": op,
                        "status": "Available",
                        "Answer": ans
                    })
                except Exception as ex:
                    print(f"⚠ Error generating {op}: {ex}")
                    skipped += 1

    return {"Questions": all_questions}


if __name__ == "__main__":
    data = generate_questions(per_op=25)
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Generated questions.json with {len(data['Questions'])} questions")
