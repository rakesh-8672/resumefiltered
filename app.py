from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import docx
from groq import Groq
import json
import re

# 🔑 PUT YOUR GROQ API KEY HERE
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = Flask(__name__)
CORS(app)


@app.route('/')
def home():
    return "Resume Analyzer API is running"


@app.route('/analyze', methods=['POST'])
def analyze_resume():

    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['resume']
        role = request.form.get('role', 'Not Specified')

        text = ""

        # PDF
        if file.filename.endswith('.pdf'):
            with pdfplumber.open(file.stream) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        # DOCX
        elif file.filename.endswith('.docx'):
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"

        else:
            return jsonify({"error": "Only PDF and DOCX allowed"}), 400

        if len(text.strip()) == 0:
            return jsonify({"error": "Could not extract resume text"}), 400

        # 🔥 VERY STRONG PROMPT (DETAILED OUTPUT)
        prompt = f"""
You are a world-class ATS Resume Analyzer used by top recruitment companies.

Return ONLY valid JSON. No explanations outside JSON.

STRICT FORMAT:

{{
  "ats_score": 0,
  "summary": "",
  "strengths": [],
  "weaknesses": [],
  "suggestions": []
}}

RULES:
- ats_score: integer 0-100 based on ATS compatibility
- summary: 5-7 lines detailed overall evaluation
- strengths: EACH point must be detailed (not keywords)
- weaknesses: EACH point must explain impact on hiring
- suggestions: VERY ACTIONABLE steps to improve resume and career

EXAMPLE STYLE:

strengths:
"Strong backend engineering experience using Node.js and MongoDB with real-world project exposure, showing ability to design scalable APIs."

weaknesses:
"Lack of cloud deployment experience limits ability to work in modern DevOps environments used in production systems."

suggestions:
"Learn AWS fundamentals and deploy at least one full-stack project using cloud services like EC2 or Render."

Resume:
{text}

Target Role:
{role}
"""

        # 🔥 GROQ AI CALL
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content

        # 🔥 SAFE JSON PARSING
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)
        except:
            result = {
                "ats_score": 0,
                "summary": content,
                "strengths": [],
                "weaknesses": [],
                "suggestions": []
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)