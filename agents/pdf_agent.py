import json
from typing import Dict, Any
import PyPDF2
import io
import google.generativeai as genai


class PDFAgent:
    def __init__(self, model, redis_client):
        self.model = model
        self.redis = redis_client

    def extract_text(self, pdf_content: str) -> str:
        # Convert string content back to bytes if needed
        if isinstance(pdf_content, str):
            pdf_content = pdf_content.encode('latin-1')

        with io.BytesIO(pdf_content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def process(self, pdf_content: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract text from PDF
            pdf_text = self.extract_text(pdf_content)

            # Analyze PDF content
            prompt = f"""
            Analyze the following document text and:
            1. Extract key fields (like invoice number, total amount, dates for invoices)
            2. Flag if total amount > 10,000
            3. Identify if document mentions any regulations (GDPR, FDA, etc.)
            4. Determine document type (invoice, policy, contract, etc.)

            Document Text:
            {pdf_text[:5000]}

            Return your response in JSON format with these keys:
            document_type, fields (dict), amount_exceeds_10k (boolean), regulations_mentioned (list)
            """

            response = self.model.generate_content(prompt)

            try:
                # Extract JSON from response
                response_text = response.text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)

                # Add classification and text sample
                analysis['classification'] = classification
                analysis['text_sample'] = pdf_text[:500]

                return analysis
            except Exception as e:
                return {
                    "error": str(e),
                    "text_sample": pdf_text[:500],
                    "classification": classification
                }
        except Exception as e:
            return {
                "error": str(e),
                "classification": classification
            }