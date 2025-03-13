import os
import logging
import json
from typing import Dict, Any, Optional, Tuple
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client
# Try to get API key from environment variable first
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    # Initialize client - if GROQ_API_KEY is None, it will use the GROQ_API_KEY environment variable
    # that might be set outside of the .env file
    client = Groq(api_key=GROQ_API_KEY)
    logger.info("Groq client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {str(e)}")
    client = None

def analyze_question(
    question_content: str, 
    question_type: str, 
    course_title: str, 
    chapter_title: str, 
    ilos: str
) -> Tuple[Optional[float], Optional[str]]:
    """
    Analyze a question using Groq API with LLaMA 3 model to:
    1. Rate its difficulty on a scale of 1-5
    2. Suggest improvements based on the ILOs
    
    Args:
        question_content: The content of the question
        question_type: The type of question (Multiple Choice, Essay, etc.)
        course_title: The title of the course
        chapter_title: The title of the chapter
        ilos: The intended learning outcomes for the chapter
        
    Returns:
        Tuple containing (difficulty_rating, improvement_suggestions)
    """
    if not client:
        logger.error("Groq client not initialized. Cannot analyze question.")
        return None, "Error: Groq client not initialized. Please check your API key."
    
    try:
        # Construct the prompt
        system_prompt = "You are an educational expert that analyzes academic questions and provides feedback."
        
        user_prompt = f"""
        Analyze this academic question and provide feedback:
        
        COURSE: {course_title}
        CHAPTER: {chapter_title}
        QUESTION TYPE: {question_type}
        INTENDED LEARNING OUTCOMES (ILOs): {ilos}
        
        QUESTION: {question_content}
        
        Please analyze this question and provide:
        
        1. DIFFICULTY RATING: Rate the question's difficulty on a scale of 1.0 to 5.0 (where 1 is easiest and 5 is hardest). Consider the complexity, cognitive load, and alignment with the ILOs.
        
        2. IMPROVEMENT SUGGESTIONS: Provide specific suggestions to improve the question's quality, clarity, and alignment with the ILOs. Consider aspects like:
           - Clarity and precision of language
           - Alignment with stated learning outcomes
           - Cognitive level (knowledge, comprehension, application, analysis, etc.)
           - Potential ambiguities or issues
           - Suggestions for better wording or structure
        
        Format your response as a JSON object with the following structure:
        {{"difficulty_rating": float, "improvement_suggestions": string}}
        """
        
        # Call the Groq API with LLaMA 3 model
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant",  # Using LLaMA 3 model
            temperature=0.3,
            max_completion_tokens=1024,
            top_p=1,
            stream=False
        )
        
        # Extract and parse the response
        response_text = response.choices[0].message.content
        logger.info(f"Received response from Groq API: {response_text[:100]}...")
        
        # Try to extract JSON from the response
        try:
            # Look for JSON pattern in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                difficulty_rating = result.get("difficulty_rating")
                improvement_suggestions = result.get("improvement_suggestions")
                
                # Validate difficulty rating
                if difficulty_rating is not None:
                    difficulty_rating = float(difficulty_rating)
                    difficulty_rating = max(1.0, min(5.0, difficulty_rating))  # Ensure it's between 1 and 5
                
                return difficulty_rating, improvement_suggestions
            else:
                logger.error("Could not find JSON in LLM response")
                # If we can't parse JSON, return the full response as the suggestion
                return None, response_text
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return None, response_text
        
    except Exception as e:
        logger.error(f"Error calling Groq API: {str(e)}")
        return None, f"Error calling Groq API: {str(e)}" 