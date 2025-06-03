import json
from typing import Dict, Any
import google.generativeai as genai


class JSONAgent:
    def __init__(self, model, redis_client):
        self.model = model
        self.redis = redis_client

    def process(self, json_content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Parse JSON first to validate
            data = json.loads(json_content)

            # Analyze JSON content
            prompt = f"""
            Analyze the following JSON data and:
            1. Validate required fields are present
            2. Check for data type consistency
            3. Identify any anomalies or potential issues

            JSON Content:
            {json.dumps(data, indent=2)[:5000]}

            Return your response in JSON format with these keys:
            valid (boolean), anomalies (list), field_types (dict), required_fields_missing (list)
            """

            response = self.model.generate_content(prompt)

            try:
                # Extract JSON from response
                response_text = response.text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)

                # Add original data and classification
                analysis['original_data'] = data
                analysis['classification'] = classification

                return analysis
            except Exception as e:
                return {
                    "error": str(e),
                    "content": data,
                    "classification": classification
                }
        except json.JSONDecodeError as e:
            return {
                "error": "Invalid JSON",
                "details": str(e),
                "classification": classification
            }