from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import docx
from groq import Groq
import json
import re

app = Flask(__name__)
CORS(app)

client = Groq(api_key="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")


@app.route('/')
def home():
    return "Resume Analyzer Running"


@app.route('/analyze', methods=['POST'])
def analyze():

    try:
        file = request.files['resume']
        role = request.form.get('role', '')

        text = ""

        if file.filename.endswith('.pdf'):
            with pdfplumber.open(file.stream) as pdf:
                for p in pdf.pages:
                    if p.extract_text():
                        text += p.extract_text()

        elif file.filename.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text

        else:
            return jsonify({"error": "Only PDF/DOCX allowed"}), 400

        # ✅ FINAL PROMPT (NO SUGGESTIONS)
        prompt = f"""
You are an expert ATS Resume Analyst and Career Coach.

Return ONLY valid JSON.

FORMAT:

{{
  "ats_score": 0,
  "summary": "",
  "strengths": [],
  "weaknesses": []
}}

🚨 RULES:

1. strengths must contain 3–5 items.
   Each item must be VERY DETAILED (15–20 lines explanation in ONE paragraph).

2. weaknesses must contain 3–5 items.
   Each item must be VERY DETAILED (15–20 lines explanation in ONE paragraph).

3. DO NOT repeat same content.

4. DO NOT write short points.

5. MUST be professional analysis style.

Resume:
{text}

Role:
{role}
"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "")

        match = re.search(r'\{.*\}', content, re.DOTALL)

        if match:
            result = json.loads(match.group())
        else:
            result = {
                "ats_score": 0,
                "summary": content,
                "strengths": [],
                "weaknesses": []
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True)
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)