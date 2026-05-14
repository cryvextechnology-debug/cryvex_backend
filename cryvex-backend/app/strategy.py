import os
import httpx
import json
import re
from app.config import settings

class CryvexStrategist:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = settings.OPENROUTER_BASE_URL
        self.model = settings.STRATEGY_MODEL
        self.system_prompt = """
        You are the Chief Strategy Agent at Cryvex, an elite AI automation and digital transformation agency. 
        You are pitching directly to a prospective client who has come to Cryvex for help. You act like a senior executive from Cryvex explaining exactly how YOUR agency (Cryvex) will solve their problems.
        
        Core Expertise: Textile, Manufacturing, E-commerce, Hyperlocal Services.
        
        Mandatory Rules for Strategy Generation:
        1. Embody the persona of a high-level agent. DO NOT use or invent a personal human name. Say "I am the Chief Strategy Agent of Cryvex".
        2. Understand the perspective: You work FOR Cryvex. You are pitching TO the client. Address the client by their exact Company Name provided. DO NOT write "Dear Cryvex" (that makes no sense).
        3. Diagnose their pain points first. Show them you understand their business.
        4. Pitch the Solution logically in two parts:
           a) FUNDAMENTAL STRATEGY: First, give them concrete, general field-based strategic advice on how any business in their exact industry should solve this problem theoretically.
           b) CRYVEX AUTOMATION: Second, explain how the Cryvex 'Digital Employee' framework will practically execute and support this exact strategy for them on autopilot.
        5. Outline an executive operational roadmap highlighting the exact steps Cryvex will take to execute this for them.
        6. Conclude with a data-driven ROI Estimation proving why hiring Cryvex is a financially sound investment.
        7. MANDATORY DISCLAIMER: Append this exact text at the very bottom: "Disclaimer: This is an AI-generated strategy and analysis, and may contain inaccuracies. Please contact Cryvex directly for a comprehensive and tailored business analysis."
        8. COMPLETENESS & CONCISENESS: Your response MUST be highly concise (under 600 words) so it finishes completely within token limits. Do not ramble. You MUST finish all sections and include the legal disclaimer at the very end.
        
        Tone & Formatting Override: 
        - Executive, authoritative, confident pitch.
        - DO NOT use any markdown symbols (no asterisks, no hash symbols, no dashes/hyphens).
        - Write strictly in raw, plain conversational text.
        - Use UPPERCASE LETTERS for section headers (e.g., EXECUTIVE OVERVIEW, STRATEGY PITCH).
        """

    async def generate_strategy(self, biz_data: dict):
        """
        Calls OpenRouter to generate a hyper-practical business strategy.
        """
        if not self.api_key or self.api_key == "your_openrouter_key_here":
            return "Error: OpenRouter API Key is missing. Please add your key to the .env file."

        business_type = biz_data.get("business_type", "General")
        problem = biz_data.get("problem", "Growth scaling")
        language = biz_data.get("language", "English")
        business_name = biz_data.get('business_name', 'your company')
        target_audience = biz_data.get("target_audience", "General public")
        primary_goal = biz_data.get("primary_goal", "Overall improvement")
        
        user_prompt = f"The Client's Company is named: {business_name}\nTheir Industry: {business_type}\nTheir Target Audience: {target_audience}\nTheir Biggest Problem: {problem}\nTheir Primary Goal: {primary_goal}\n\nCRITICAL LANGUAGE DIRECTIVE: You MUST generate your ENTIRE consultation, response, and roadmap strictly in exactly this language: {language}. Do not provide an English translation unless requested.\n\nPlease act as the Chief Strategy Agent. Analyze their situation, give executive advice, and propose a highly customized Cryvex digital workforce strategy directly tailored to {business_name} in {language}. Specifically outline how to overcome their problem and achieve their primary goal for their specific target audience."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://cryvex.ai", # Optional info for OpenRouter
            "X-Title": "Cryvex Strategy Engine", # Optional info for OpenRouter
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # DeepSeek-R1 generates large <think>...</think> blocks. We must strip this out so it's not rendered to the user.
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                
                # Forcefully strip unwanted markdown formatting symbols (*, #, _, -) to guarantee clean memo plain text
                content = content.replace('*', '').replace('#', '').replace('_', '')
                
                return content.strip()
            except Exception as e:
                return f"Error generating strategy: {str(e)}"

# Global instance will be created in main.py
