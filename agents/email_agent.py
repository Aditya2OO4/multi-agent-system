import json
from typing import Dict, Any
import re
import google.generativeai as genai


class EmailAgent:
    def __init__(self, model, redis_client):
        self.model = model
        self.redis = redis_client

    def process(self, email_content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        # Extract structured fields using Gemini
        prompt = f"""
        Analyze the following email and extract:
        1. Sender information (name, email)
        2. Urgency level (low, medium, high)
        3. Main issue or request
        4. Tone (polite, angry, neutral, threatening)

        Also identify if this is an escalation.

        Email Content:
        {email_content[:5000]}

        Return your response in JSON format with these keys:
        sender, urgency, issue, tone, is_escalation
        """

        response = self.model.generate_content(prompt)

        try:
            # Extract JSON from response
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            extracted_data = json.loads(json_str)

            # Add classification info
            extracted_data['classification'] = classification

            return extracted_data
        except Exception as e:
            return {
                "error": str(e),
                "content": email_content,
                "classification": classification
            }