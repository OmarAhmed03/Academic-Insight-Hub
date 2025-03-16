import streamlit as st
import pandas as pd
from database import get_db
from models import Course, Chapter, Question
from datetime import datetime
import logging
from utils import show_success, show_error, rerun
from llm_utils import analyze_question
import json
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_question_generator():
    """Display the question generator page."""
    st.markdown("## Add New Question")
    st.markdown("Enter the question details below. The AI will automatically determine the difficulty level, estimated time, and appropriate student level.")
    
    # Initialize session state for form reset
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # Reset form if it was just submitted
    if st.session_state.form_submitted:
        st.session_state.form_submitted = False
        st.rerun()
    
    try:
        db = next(get_db())
        
        # Get all courses and chapters
        courses = db.query(Course).all()
        
        if not courses:
            st.warning("No courses available. Please add a course first.")
            return
        
        # Course selection
        selected_course_id = st.selectbox(
            "Select Course",
            options=[(c.id, c.title) for c in courses],
            format_func=lambda x: x[1],
            key="question_course"
        )
        
        # Get chapters for the selected course
        chapters = db.query(Chapter).filter_by(course_id=selected_course_id[0]).all()
        
        if not chapters:
            st.warning(f"No chapters available for the selected course. Please add a chapter first.")
            return
        
        # Chapter selection
        selected_chapter_id = st.selectbox(
            "Select Chapter",
            options=[(c.id, c.title) for c in chapters],
            format_func=lambda x: x[1],
            key="question_chapter"
        )
        
        # Get the selected chapter and course
        selected_chapter = db.query(Chapter).get(selected_chapter_id[0])
        selected_course = db.query(Course).get(selected_course_id[0])
        
        if not selected_chapter:
            st.warning("Selected chapter not found.")
            return
        
        # Question content
        question_content = st.text_area(
            "Question Content", 
            height=150,
            help="Enter the complete question text here.",
            key="question_content"
        )
        
        # Question type selection
        question_type = st.selectbox(
            "Question Type",
            options=["Multiple Choice", "True/False", "Short Answer"],
            help="Select the type of question"
        )
        
        # Correct answer
        correct_answer = st.text_area(
            "Correct Answer", 
            height=100,
            help="Enter the correct answer for this question",
            key="correct_answer"
        )
        
        # Explanation
        explanation = st.text_area(
            "Explanation",
            height=100,
            help="Provide an explanation for why this is the correct answer",
            key="explanation"
        )
        
        # For multiple choice, add options
        options = []
        if question_type == "Multiple Choice":
            st.markdown("### Answer Options")
            st.info("Enter 4 options. Make sure one matches the correct answer exactly.")
            for i in range(4):
                option = st.text_input(f"Option {chr(65+i)}", key=f"option_{i}")
                if option:
                    options.append(f"{chr(65+i)}. {option}")
        
        # Add question button
        if st.button("Add Question"):
            if not question_content or not correct_answer or not explanation:
                show_error("Please fill in all required fields: question content, correct answer, and explanation.")
                return
                
            if question_type == "Multiple Choice" and (len(options) != 4 or not all(options)):
                show_error("Please provide all 4 options for multiple choice questions.")
                return
                
            try:
                # First analyze the question with AI
                with st.spinner("AI is analyzing the question..."):
                    # Call analyze_question function to get difficulty and other metrics
                    difficulty_rating, analysis_text = analyze_question(
                        question_content=question_content,
                        question_type=question_type,
                        course_title=selected_course.title,
                        chapter_title=selected_chapter.title,
                        ilos=selected_chapter.ilos
                    )
                    
                    if difficulty_rating is None:
                        show_error("Failed to analyze question. Please try again.")
                        return
                    
                    # Parse the analysis text to extract time and level
                    try:
                        # Extract time (assuming it's mentioned in minutes)
                        time_match = re.search(r'(\d+)\s*minutes?', analysis_text, re.IGNORECASE)
                        estimated_time = int(time_match.group(1)) if time_match else 5  # default to 5 minutes
                        
                        # Extract student level
                        level_match = re.search(r'(beginner|intermediate|advanced)', analysis_text, re.IGNORECASE)
                        student_level = level_match.group(1).capitalize() if level_match else "Intermediate"
                        
                        # Format correct answer for multiple choice questions
                        final_correct_answer = correct_answer
                        if question_type == "Multiple Choice":
                            # Store options in the correct_answer field with format: correct_answer|option1|option2|option3|option4
                            final_correct_answer = f"{correct_answer}|{options[0]}|{options[1]}|{options[2]}|{options[3]}"
                        
                        # Create new question with analyzed attributes
                        new_question = Question(
                            chapter_id=selected_chapter_id[0],
                            content=question_content,
                            question_type=question_type,
                            correct_answer=final_correct_answer,
                            explanation=explanation,
                            difficulty=float(difficulty_rating),
                            estimated_time=estimated_time,
                            student_level=student_level,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        db.add(new_question)
                        db.commit()
                        
                        # Show success message with AI analysis
                        success_msg = f"""Question added successfully! 
                        
                        AI Analysis Results:
                        • Difficulty Rating: {difficulty_rating}/5.0
                        • Estimated Time: {estimated_time} minutes
                        • Student Level: {student_level}
                        
                        Analysis Details:
                        {analysis_text}"""
                        
                        show_success(success_msg)
                        
                        # Set form_submitted flag to trigger reset on next rerun
                        st.session_state.form_submitted = True
                        st.rerun()
                        
                    except Exception as e:
                        logger.error(f"Error parsing analysis results: {str(e)}")
                        show_error(f"Error analyzing question: {str(e)}")
                        return
                    
            except Exception as e:
                logger.error(f"Error adding question: {str(e)}")
                show_error(f"Error: {str(e)}")
                if 'db' in locals():
                    db.rollback()
    
    except Exception as e:
        logger.error(f"Error in question generator: {str(e)}")
        show_error(f"Error: {str(e)}")

# For backward compatibility
if __name__ == "__main__":
    show_question_generator() 