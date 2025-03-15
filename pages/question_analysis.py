import streamlit as st
from database import get_db
from models import Question, Chapter, Course
from utils import show_error, show_success, show_info
import llm_utils
import logging
from datetime import datetime
import os
from groq import Groq
import json
from analysis_display import display_analysis_results
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page title
st.title("Question Analysis with AI")

# Check if user is logged in
if "user" not in st.session_state:
    show_error("Please log in to access this feature.")
    st.stop()

# Check if user has appropriate role
user_role = st.session_state.user.get("role", "").lower()
if user_role not in ["professor", "admin", "teaching_assistant"]:
    show_error("You don't have permission to access this feature.")
    st.stop()

# Check if Groq API key is set in Streamlit secrets
try:
    groq_api_key = st.secrets["groq_api_key"]
except Exception:
    st.error("⚠️ Groq API key is not set in Streamlit secrets.")
    st.info("Please set up your Groq API key in the Streamlit secrets configuration.")
    st.markdown("Get your API key from [Groq Console](https://console.groq.com/)")
    st.stop()

# Main content
st.write("This tool uses AI to analyze questions, rate their difficulty, and suggest improvements based on the course's Intended Learning Outcomes (ILOs).")

# Option to analyze existing question or create a new one
analysis_option = st.radio(
    "Choose an option:",
    ["Analyze Existing Question", "Analyze New Question"]
)

def analyze_question_with_ai(question_content, question_type):
    """
    Analyze a question using the Groq API.
    
    Args:
        question_content: The content of the question
        question_type: The type of question (Multiple Choice, Essay, etc.)
        
    Returns:
        A dictionary with analysis results
    """
    try:
        # Get Groq client using our utility function
        client = llm_utils.get_groq_client()
        if not client:
            show_error("Failed to initialize Groq client. Please check your API key configuration.")
            logger.error("Failed to initialize Groq client")
            return None
        
        # Create prompt for analysis
        prompt = f"""
        You are an expert in educational assessment. Please analyze the following question:
        
        Question: {question_content}
        Question Type: {question_type}
        
        Provide the following analysis:
        1. Difficulty rating (1-5 scale, where 1 is easiest and 5 is hardest)
        2. Estimated time to answer (in minutes)
        3. Appropriate student level (Beginner, Intermediate, Advanced)
        4. Suggested improvements to the question
        5. Relevant tags for categorizing this question
        
        Format your response as a JSON object with the following keys:
        difficulty, estimated_time, student_level, improvements, tags
        """
        
        # Call Groq API
        with st.spinner("Analyzing question with AI..."):
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are an expert in educational assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            # Extract the response
            response_text = response.choices[0].message.content
            
            # Try to parse as JSON
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # If not valid JSON, try to extract structured data
                analysis = {}
                
                if "difficulty" in response_text:
                    try:
                        difficulty_section = response_text.split("difficulty")[1].split("estimated_time")[0]
                        analysis["difficulty"] = float(re.search(r'\d+\.?\d*', difficulty_section).group())
                    except:
                        analysis["difficulty"] = 3.0
                
                if "estimated_time" in response_text:
                    try:
                        time_section = response_text.split("estimated_time")[1].split("student_level")[0]
                        analysis["estimated_time"] = int(re.search(r'\d+', time_section).group())
                    except:
                        analysis["estimated_time"] = 5
                
                if "student_level" in response_text:
                    try:
                        level_section = response_text.split("student_level")[1].split("improvements")[0]
                        analysis["student_level"] = level_section.strip()
                    except:
                        analysis["student_level"] = "Intermediate"
                
                if "improvements" in response_text:
                    try:
                        improvements_section = response_text.split("improvements")[1].split("tags")[0]
                        analysis["improvements"] = improvements_section.strip()
                    except:
                        analysis["improvements"] = "No specific improvements suggested."
                
                if "tags" in response_text:
                    try:
                        tags_section = response_text.split("tags")[1].strip()
                        analysis["tags"] = tags_section.strip()
                    except:
                        analysis["tags"] = "education, assessment"
            
            return analysis
    
    except Exception as e:
        logger.error(f"Error analyzing question with AI: {str(e)}")
        show_error(f"Error analyzing question: {str(e)}")
        return None

def show_question_analysis():
    """Display the question analysis page."""
    st.markdown("## Question Analysis")
    
    # Check if Groq API key is set
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        st.error("""
        Groq API key not found. Please set the GROQ_API_KEY environment variable.
        
        1. Get an API key from https://console.groq.com/
        2. Add it to your .env file: GROQ_API_KEY=your_api_key_here
        3. Restart the application
        """)
        return
    
    # Check if analyzing an existing question
    if "analyzing_question_id" in st.session_state:
        question_id = st.session_state.analyzing_question_id
        analyze_existing_question(question_id)
        return
    
    # Tabs for analyzing existing vs new questions
    tab1, tab2 = st.tabs(["Analyze Existing Question", "Analyze New Question"])
    
    with tab1:
        analyze_existing_question_tab()
    
    with tab2:
        analyze_new_question_tab()

def analyze_existing_question(question_id):
    """Analyze an existing question by ID."""
    try:
        db = next(get_db())
        
        # Get question details
        question = db.query(Question).get(question_id)
        
        if not question:
            show_error("Question not found.")
            return
        
        # Display question details with improved styling
        st.markdown("<h3 style='color: #2d3748;'>Question Details</h3>", unsafe_allow_html=True)
        
        # Custom CSS for question details
        st.markdown("""
        <style>
        .question-details {
            background-color: #e8f4f8;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            border-left: 5px solid #4a86e8;
        }
        .detail-label {
            font-weight: 600;
            color: #2c5282;
        }
        .detail-value {
            font-weight: normal;
            color: #2d3748;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display question details in a styled container
        st.markdown(f"""
        <div class="question-details">
            <p><span class="detail-label">Content:</span> <span class="detail-value">{question.content}</span></p>
            <p><span class="detail-label">Type:</span> <span class="detail-value">{question.question_type}</span></p>
            <p><span class="detail-label">Current Difficulty:</span> <span class="detail-value">{question.difficulty}/5</span></p>
            <p><span class="detail-label">Current Estimated Time:</span> <span class="detail-value">{question.estimated_time} minutes</span></p>
            <p><span class="detail-label">Current Student Level:</span> <span class="detail-value">{question.student_level}</span></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Button to analyze
        if st.button("Analyze with AI"):
            analysis = analyze_question_with_ai(question.content, question.question_type)
            
            if analysis:
                # Display analysis results in a well-organized, visually appealing card-based layout
                display_analysis_results(analysis)
                
                # Optionally show raw output in an expander
                with st.expander("View Raw Analysis Output"):
                    st.json(analysis)
                
                # Update question button
                if st.button("Update Question with AI Suggestions"):
                    try:
                        question.difficulty = analysis.get('difficulty', question.difficulty)
                        question.estimated_time = analysis.get('estimated_time', question.estimated_time)
                        question.student_level = analysis.get('student_level', question.student_level)
                        question.tags = analysis.get('tags', question.tags)
                        
                        db.commit()
                        show_success("Question updated successfully with AI suggestions!")
                    except Exception as e:
                        logger.error(f"Error updating question: {str(e)}")
                        show_error(f"Error updating question: {str(e)}")
        
        # Button to go back
        if st.button("Back to Question Bank"):
            st.session_state.pop("analyzing_question_id", None)
            st.rerun()
    
    except Exception as e:
        logger.error(f"Error analyzing existing question: {str(e)}")
        show_error(f"Error: {str(e)}")

def analyze_existing_question_tab():
    """Tab for analyzing existing questions."""
    st.markdown("### Select a Question to Analyze")
    
    try:
        db = next(get_db())
        
        # Get courses for filtering
        courses = db.query(Course).all()
        
        if not courses:
            st.info("No courses found. Please add a course first.")
            return
        
        # Course selection
        selected_course = st.selectbox(
            "Select Course",
            options=[(0, "All Courses")] + [(c.id, c.title) for c in courses],
            format_func=lambda x: x[1],
            key="existing_question_course"
        )
        
        # Get chapters based on selected course
        if selected_course[0] == 0:
            chapters = db.query(Chapter).all()
        else:
            chapters = db.query(Chapter).filter_by(course_id=selected_course[0]).all()
        
        if not chapters:
            st.info("No chapters found for the selected course.")
            return
        
        # Chapter selection
        selected_chapter = st.selectbox(
            "Select Chapter",
            options=[(0, "All Chapters")] + [(c.id, c.title) for c in chapters],
            format_func=lambda x: x[1],
            key="existing_question_chapter"
        )
        
        # Get questions based on filters
        query = db.query(Question)
        
        if selected_chapter[0] != 0:
            query = query.filter_by(chapter_id=selected_chapter[0])
        elif selected_course[0] != 0:
            query = query.join(Chapter).filter(Chapter.course_id == selected_course[0])
        
        questions = query.all()
        
        if not questions:
            st.info("No questions found for the selected filters.")
            return
        
        # Question selection
        selected_question = st.selectbox(
            "Select Question",
            options=[(q.id, q.content[:100] + "..." if len(q.content) > 100 else q.content) for q in questions],
            format_func=lambda x: x[1],
            key="existing_question_select"
        )
        
        # Button to analyze
        if st.button("Analyze Selected Question"):
            st.session_state.analyzing_question_id = selected_question[0]
            st.rerun()
    
    except Exception as e:
        logger.error(f"Error in analyze_existing_question_tab: {str(e)}")
        show_error(f"Error: {str(e)}")

def analyze_new_question_tab():
    """Tab for analyzing new questions."""
    st.markdown("### Create and Analyze a New Question")
    
    try:
        db = next(get_db())
        
        # Get courses
        courses = db.query(Course).all()
        
        if not courses:
            st.info("No courses found. Please add a course first.")
            return
        
        # Course selection
        selected_course = st.selectbox(
            "Select Course",
            options=[(c.id, c.title) for c in courses],
            format_func=lambda x: x[1],
            key="new_question_course"
        )
        
        # Get chapters for selected course
        chapters = db.query(Chapter).filter_by(course_id=selected_course[0]).all()
        
        if not chapters:
            st.info("No chapters found for the selected course. Please add a chapter first.")
            return
        
        # Chapter selection
        selected_chapter = st.selectbox(
            "Select Chapter",
            options=[(c.id, c.title) for c in chapters],
            format_func=lambda x: x[1],
            key="new_question_chapter"
        )
        
        # Question content
        question_content = st.text_area("Question Content", height=150)
        
        # Question type
        question_type = st.selectbox(
            "Question Type",
            options=["Multiple Choice", "True/False", "Essay", "Short Answer"],
            key="new_question_type"
        )
        
        # Button to analyze
        if st.button("Analyze New Question") and question_content:
            analysis = analyze_question_with_ai(question_content, question_type)
            
            if analysis:
                # Display analysis results in a well-organized, visually appealing card-based layout
                display_analysis_results(analysis)
                
                # Optionally show raw output in an expander
                with st.expander("View Raw Analysis Output"):
                    st.json(analysis)
                
                # Store analysis in session state
                st.session_state.new_question_analysis = analysis
                st.session_state.new_question_content = question_content
                st.session_state.new_question_type = question_type
                st.session_state.new_question_chapter_id = selected_chapter[0]
                
                # Option to edit question based on suggestions
                edited_content = st.text_area(
                    "Edit Question Based on Suggestions",
                    value=question_content,
                    height=150
                )
                
                # Add question button
                if st.button("Add Question to Database"):
                    try:
                        # Create new question
                        new_question = Question(
                            chapter_id=selected_chapter[0],
                            content=edited_content,
                            difficulty=analysis.get('difficulty', 3.0),
                            estimated_time=analysis.get('estimated_time', 5),
                            student_level=analysis.get('student_level', 'Intermediate'),
                            question_type=question_type,
                            tags=analysis.get('tags', ''),
                            correct_answer="",
                            explanation=""
                        )
                        
                        db.add(new_question)
                        db.commit()
                        
                        show_success("Question added successfully!")
                        
                        # Clear session state
                        st.session_state.pop("new_question_analysis", None)
                        st.session_state.pop("new_question_content", None)
                        st.session_state.pop("new_question_type", None)
                        st.session_state.pop("new_question_chapter_id", None)
                        
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error adding question: {str(e)}")
                        show_error(f"Error adding question: {str(e)}")
        elif not question_content and st.button("Analyze New Question"):
            show_error("Please enter question content.")
    
    except Exception as e:
        logger.error(f"Error in analyze_new_question_tab: {str(e)}")
        show_error(f"Error: {str(e)}")

# For backward compatibility - this will be called when the file is run directly
if __name__ == "__main__":
    st.title("Question Analysis")
    show_question_analysis()

# If editing a question before adding
if "editing_question_content" in st.session_state:
    st.subheader("Edit Question Before Adding")
    edited_content = st.text_area("Question Content", value=st.session_state["editing_question_content"], height=150)
    edited_type = st.selectbox("Question Type", options=["Multiple Choice", "True/False", "Essay", "Short Answer"], index=["Multiple Choice", "True/False", "Essay", "Short Answer"].index(st.session_state["editing_question_type"]))
    edited_difficulty = st.slider("Difficulty", min_value=1.0, max_value=5.0, value=st.session_state["editing_question_difficulty"], step=0.1)
    
    if st.button("Add Edited Question"):
        # Create new question with edited content
        new_question = Question(
            chapter_id=st.session_state["editing_question_chapter_id"],
            content=edited_content,
            difficulty=edited_difficulty,
            question_type=edited_type,
            student_level="Intermediate",  # Default value
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            db = next(get_db())
            db.add(new_question)
            db.commit()
            show_success("Question added successfully!")
            
            # Clear session state
            for key in ["editing_question_content", "editing_question_type", "editing_question_difficulty", "editing_question_chapter_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.rerun()
        except Exception as e:
            db.rollback()
            show_error(f"Error adding question: {str(e)}")
    
    if st.button("Cancel Editing"):
        # Clear session state
        for key in ["editing_question_content", "editing_question_type", "editing_question_difficulty", "editing_question_chapter_id"]:
            if key in st.session_state:
                del st.session_state[key]
        
        st.rerun()

# Add navigation buttons
st.markdown("---")
if st.button("Back to Questions"):
    st.switch_page("pages/view.py")