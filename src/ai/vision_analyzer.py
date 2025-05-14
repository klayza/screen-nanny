from openai import OpenAI
import base64
import os
from screen_monitor.system_info import SystemMonitor 
from dotenv import load_dotenv


class VisionAnalyzer:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.token_usage = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }

    def format_window_info(self, window_info):
        """Format window information for display"""
        return f"""
        Window Title: {window_info['window_title']}
        Process Name: {window_info['process_name']}
        """
    
    def analyze_window_title(self, window_info, focus_description=None):
        """Analyze window title and process name to determine if it's distracting"""
        if focus_description:
            prompt = f"""You are a productivity assistant. The user is trying to focus on: {focus_description}

            Important: 
            - Do not consider music as a distraction.
            - ONLY when the title is CLEAR that it is a distraction, mark it as a distraction.
            - Do not mark it as a distraction if it is a broad assumption.

            Analyze this window information and determine if it's aligned with their goal:
            {self.format_window_info(window_info)}
            
            Respond in this format:
            - Is_Distracted: [true/false]
            - Reason: [brief explanation]
            - Timeout: [lock the user out for x seconds. ex: 5, 20, max 120]
            """
        else:
            prompt = f"""You are a productivity assistant. Analyze this window information and determine if it appears to be:
            1. Productive/Neutral (coding, documents, email, music, learning, etc.) (any music or educational video is fine)
            2. Distraction (social media, youtube, twitter, facebook, netflix, etc.) 
            Important: 
            - Do not consider music as a distraction.
            - ONLY when the title is CLEAR that it is a distraction, mark it as a distraction.
            - Do not mark it as a distraction if it is a broad assumption.

            {self.format_window_info(window_info)}
            
            Respond in this format:
            - Is_Distracted: [true/false]
            - Reason: [brief explanation, 1 tiny sentence, in australian accent]
            - Timeout: [lock the user out for x seconds. ex: 5, 20, 120]
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        # Track token usage
        self.token_usage["prompt_tokens"] += response.usage.prompt_tokens
        self.token_usage["completion_tokens"] += response.usage.completion_tokens
        self.token_usage["total_tokens"] += response.usage.total_tokens
        
        return self._parse_response(response.choices[0].message.content)
    
    def encode_image(self, image_path):
        """Convert image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_screen(self, image_path, focus_description=None):
        """Analyze screenshot and determine if it's distracting (expensive fallback method)"""

        # DISABLED [NOT PRACTICAL]
        return

        base64_image = self.encode_image(image_path)
        
        if focus_description:
            prompt = f"""You are a productivity assistant. The user is trying to focus on: {focus_description}
            
            Analyze this screenshot and determine if the content is aligned with their goal.
            If it's not aligned, explain why it's distracting.
            
            Respond in this format:
            - Is_Distracted: [true/false]
            - Reason: [brief explanation]
            - Timeout: [lock the user out for x seconds. ex: 5, 20, 120]
            """
        else:
            prompt = """You are a productivity assistant. Analyze this screenshot and determine if the content appears to be:
            1. Productive work (coding, documents, email, etc.)
            2. General time-wasting (social media, entertainment, etc.)
            
            Respond in this format:
            - Is_Distracted: [true/false]
            - Reason: [brief explanation]
            - Timeout: [lock the user out for x seconds. ex: 5, 20, 120]
            """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        # Track token usage
        self.token_usage["prompt_tokens"] += response.usage.prompt_tokens
        self.token_usage["completion_tokens"] += response.usage.completion_tokens
        self.token_usage["total_tokens"] += response.usage.total_tokens
        
        return self._parse_response(response.choices[0].message.content)
    
    def _parse_response(self, content):
        """Parse the AI response into a structured format"""
        lines = content.split('\n')
        result = {
            "is_distracted": False,
            "reason": "",
            "timeout": 10
        }
        
        for line in lines:
            if "Is_Distracted:" in line:
                result["is_distracted"] = "true" in line.lower()
            elif "Reason:" in line:
                result["reason"] = line.split("Reason:")[1].strip()
            elif "Timeout:" in line:
                result["timeout"] = int(line.split("Timeout:")[1].strip())
        
        return result
    
    def get_token_usage(self):
        """Return current token usage statistics"""
        return self.token_usage 