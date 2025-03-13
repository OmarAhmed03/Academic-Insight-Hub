import streamlit as st
from database import get_db
from models import Course, Chapter, Question
from utils import show_success, show_error
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_course():
    """Function to add a new course."""
    st.subheader("Add New Course")
    
    with st.form("add_course_form"):
        title = st.text_input("Course Title")
        description = st.text_area("Course Description")
        submit = st.form_submit_button("Add Course")
        
    if submit:
        if not title:
            show_error("Course title is required")
            return
            
        try:
            db = next(get_db())
            
            # Create new course
            new_course = Course(
                title=title,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                created_by=st.session_state.user["id"]
            )
            
            db.add(new_course)
            db.commit()
            
            show_success(f"Course '{title}' added successfully!")
            
            # Clear form without full page refresh
            st.query_params.clear()
            # Don't call rerun() here to avoid session loss
            
        except Exception as e:
            logger.error(f"Error adding course: {str(e)}")
            show_error(f"Error adding course: {str(e)}")

def add_chapter():
    """Function to add a new chapter."""
    st.subheader("Add New Chapter")
    
    db = next(get_db())
    courses = db.query(Course).all()
    
    if not courses:
        st.warning("No courses available. Please add a course first.")
        return
    
    with st.form("add_chapter_form"):
        course_id = st.selectbox(
            "Select Course",
            options=[(c.id, c.title) for c in courses],
            format_func=lambda x: x[1]
        )
        
        title = st.text_input("Chapter Title")
        summary = st.text_area("Chapter Summary")
        ilos = st.text_area("Intended Learning Outcomes (One per line)")
        
        submit = st.form_submit_button("Add Chapter")
        
    if submit:
        if not title:
            show_error("Chapter title is required")
            return
            
        try:
            # Create new chapter
            new_chapter = Chapter(
                course_id=course_id[0],
                title=title,
                summary=summary,
                ilos=ilos,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_chapter)
            db.commit()
            
            show_success(f"Chapter '{title}' added successfully!")
            
            # Clear form without full page refresh
            st.query_params.clear()
            # Don't call rerun() here to avoid session loss
            
        except Exception as e:
            logger.error(f"Error adding chapter: {str(e)}")
            show_error(f"Error adding chapter: {str(e)}")

def add_question():
    """Function to add a new question."""
    st.subheader("Add New Question")
    
    db = next(get_db())
    chapters = db.query(Chapter).join(Course).all()
    
    if not chapters:
        st.warning("No chapters available. Please add a chapter first.")
        return
    
    with st.form("add_question_form"):
        chapter_id = st.selectbox(
            "Select Chapter",
            options=[(c.id, f"{c.course.title} - {c.title}") for c in chapters],
            format_func=lambda x: x[1]
        )
        
        content = st.text_area("Question Content")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.slider("Difficulty (1-5)", 1.0, 5.0, 3.0, 0.5)
            estimated_time = st.number_input("Estimated Time (minutes)", min_value=1, value=5)
        
        with col2:
            student_level = st.selectbox("Student Level", ["Beginner", "Intermediate", "Advanced"])
            tags = st.text_input("Tags (comma-separated)")
        
        question_type = st.selectbox("Question Type", ["Multiple Choice", "True/False", "Essay", "Short Answer"])
        
        correct_answer = st.text_area("Correct Answer")
        explanation = st.text_area("Explanation")
        
        submit = st.form_submit_button("Add Question")
        
    if submit:
        if not content:
            show_error("Question content is required")
            return
            
        try:
            # Create new question
            new_question = Question(
                chapter_id=chapter_id[0],
                content=content,
                difficulty=difficulty,
                estimated_time=estimated_time,
                student_level=student_level,
                tags=tags,
                question_type=question_type,
                correct_answer=correct_answer,
                explanation=explanation,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_question)
            db.commit()
            
            show_success("Question added successfully!")
            
            # Clear form without full page refresh
            st.query_params.clear()
            # Don't call rerun() here to avoid session loss
            
        except Exception as e:
            logger.error(f"Error adding question: {str(e)}")
            show_error(f"Error adding question: {str(e)}")

# Main function for backward compatibility
def main():
    """Main function to display the add page."""
    st.title("Add Content")
    
    # Create tabs for different content types
    tab1, tab2, tab3 = st.tabs(["Add Course", "Add Chapter", "Add Question"])
    
    with tab1:
        add_course()
    
    with tab2:
        add_chapter()
    
    with tab3:
        add_question()

# For backward compatibility - this will be called when the file is run directly
if __name__ == "__main__":
    main()
