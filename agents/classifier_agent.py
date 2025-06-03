import json
from typing import Dict, Any
import google.generativeai as genai


class ClassifierAgent:
    def __init__(self, model, db_conn_func):
        self.model = model
        self.get_db_conn = db_conn_func
        self.few_shot_examples = """
        Examples of format and intent classification:

        1. Input: "Dear Support, I'm unhappy with your service. My order #12345 was delayed by 2 weeks."
           Format: email
           Intent: complaint

        2. Input: {"invoice_id": "INV-2023-456", "total": 12500.00, "due_date": "2023-12-31"}
           Format: json
           Intent: invoice

        3. Input: "This document outlines the new GDPR compliance requirements..."
           Format: pdf
           Intent: regulation

        4. Input: "We would like to request a quote for 100 units of product X."
           Format: email
           Intent: rfq

        5. Input: {"transaction_id": "TX-987", "amount": 15000, "flagged": true}
           Format: json
           Intent: fraud_risk
        """

    def classify(self, content: str, input_type: str) -> Dict[str, Any]:
        prompt = f"""
        {self.few_shot_examples}

        Analyze the following input and determine:
        1. The format (email, json, pdf)
        2. The business intent (rfq, complaint, invoice, regulation, fraud_risk)

        Input:
        {content[:5000]}

        Provide your response in JSON format with keys: format, intent, confidence
        """

        response = self.model.generate_content(prompt)
        try:
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            classification = json.loads(json_str)

            if 'format' not in classification or 'intent' not in classification:
                raise ValueError("Invalid classification format")

            # Log classification to database
            conn = self.get_db_conn()
            try:
                conn.execute(
                    "INSERT INTO classifications (content_sample, classification_result) VALUES (?, ?)",
                    (content[:500], json.dumps(classification)))
                conn.commit()
            finally:
                conn.close()

            return classification
        except Exception as e:
            return {
                "format": input_type,
                "intent": "unknown",
                "confidence": 0.5,
                "error": str(e)
            }