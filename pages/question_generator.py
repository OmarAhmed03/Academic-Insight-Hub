import streamlit as st
import pandas as pd
from database import get_db
from models import Course, Chapter, Question
from datetime import datetime
import logging
from utils import show_success, show_error, rerun
from llm_utils import generate_questions, analyze_question

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_question_generator():
    """Display the question generator page."""
    st.markdown("## AI Question Generator")
    st.markdown("Generate questions for a chapter using artificial intelligence.")
    
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
            key="ai_gen_course"
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
            key="ai_gen_chapter"
        )
        
        # Get the selected chapter
        selected_chapter = db.query(Chapter).get(selected_chapter_id[0])
        
        if not selected_chapter:
            st.warning("Selected chapter not found.")
            return
        
        # Display chapter summary and ILOs
        st.markdown("### Chapter Information")
        st.markdown(f"**Title:** {selected_chapter.title}")
        st.markdown(f"**Summary:**")
        st.markdown(selected_chapter.summary)
        st.markdown(f"**Intended Learning Outcomes (ILOs):**")
        st.markdown(selected_chapter.ilos)
        
        # Get existing questions for the chapter as examples
        existing_questions = db.query(Question).filter_by(chapter_id=selected_chapter_id[0]).limit(3).all()
        existing_questions_text = []
        
        if existing_questions:
            for q in existing_questions:
                q_text = f"Question: {q.content}\n"
                q_text += f"Type: {q.question_type}\n"
                q_text += f"Difficulty: {q.difficulty}\n"
                q_text += f"Correct Answer: {q.correct_answer}\n"
                existing_questions_text.append(q_text)
        
        # Generation parameters
        st.markdown("### Generation Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            num_questions = st.number_input("Number of Questions", min_value=1, max_value=10, value=3)
            difficulty_level = st.selectbox(
                "Difficulty Level", 
                ["easy", "medium", "hard", "mixed"],
                index=3  # Default to mixed
            )
        
        with col2:
            question_types = st.multiselect(
                "Question Types",
                ["Multiple Choice", "True/False", "Short Answer", "Essay"],
                default=["Multiple Choice", "True/False"]
            )
            
            if not question_types:
                st.warning("Please select at least one question type.")
                question_types = ["Multiple Choice"]
            
            model_choice = st.selectbox(
                "AI Model", 
                [
                    "LLaMA-3 (8B Instant)",
                    "LLaMA-3 (70B)",
                    "DeepSeek (6.7B)",
                    "Mixtral (8x7B)"
                ],
                index=0  # Default to LLaMA-3 8B
            )
            
            # Map selection to actual model ID
            model_mapping = {
                "LLaMA-3 (8B Instant)": "llama-3.1-8b-instant",
                "LLaMA-3 (70B)": "llama-3.1-70b-versatile",
                "DeepSeek (6.7B)": "deepseek-coder-instruct-6.7b",
                "Mixtral (8x7B)": "mixtral-8x7b-32768"
            }
            
            selected_model = model_mapping[model_choice]
        
        # Set a session state flag for generation
        if "generating_questions" not in st.session_state:
            st.session_state.generating_questions = False
            
        # Generation button
        generate_button = st.button("Generate Questions", type="primary")
        
        if generate_button:
            if not question_types:
                show_error("Please select at least one question type.")
                return
                
            # Set the generating flag to true
            st.session_state.generating_questions = True
            
            # Store parameters in session state to preserve them
            st.session_state.generation_params = {
                "course_id": selected_course_id[0],
                "chapter_id": selected_chapter_id[0],
                "num_questions": num_questions,
                "difficulty_level": difficulty_level,
                "question_types": question_types,
                "model": selected_model,
                "model_name": model_choice
            }
            
            # Use st.rerun() instead of st.experimental_rerun()
            st.rerun()
        
        # Execute generation if the flag is set
        if st.session_state.get("generating_questions"):
            with st.spinner("Generating questions... This may take a moment."):
                try:
                    # Get parameters from session state
                    params = st.session_state.generation_params
                    
                    # Get selected course and chapter
                    selected_course = db.query(Course).get(params["course_id"])
                    selected_chapter = db.query(Chapter).get(params["chapter_id"])
                    
                    # Generate questions with selected model
                    generated_questions = generate_questions(
                        course_title=selected_course.title,
                        chapter_title=selected_chapter.title,
                        chapter_summary=selected_chapter.summary,
                        ilos=selected_chapter.ilos,
                        num_questions=params["num_questions"],
                        difficulty_level=params["difficulty_level"],
                        question_types=params["question_types"],
                        existing_questions=existing_questions_text,
                        model=params["model"]
                    )
                    
                    if not generated_questions:
                        show_error("Failed to generate questions. Please try again later.")
                        st.session_state.generating_questions = False
                        return
                    
                    # Store generated questions in session state
                    st.session_state.generated_questions = generated_questions
                    st.success(f"Successfully generated {len(generated_questions)} questions using {params['model_name']}!")
                    
                    # Reset the generating flag
                    st.session_state.generating_questions = False
                    
                except Exception as e:
                    logger.error(f"Error generating questions: {str(e)}")
                    show_error(f"Error generating questions: {str(e)}")
                    st.session_state.generating_questions = False
        
        # Display generated questions
        if "generated_questions" in st.session_state and st.session_state.generated_questions:
            st.markdown("### Generated Questions")
            
            # Add button to save all questions
            save_all = st.button("Save All Questions to Database")
            
            for i, question in enumerate(st.session_state.generated_questions):
                with st.expander(f"Question {i+1}: {question['question_content'][:100]}...", expanded=True):
                    st.markdown(f"**Question:**")
                    st.markdown(question['question_content'])
                    
                    st.markdown(f"**Question Type:** {question['question_type']}")
                    st.markdown(f"**Difficulty:** {question['difficulty']}")
                    st.markdown(f"**Estimated Time:** {question.get('estimated_time', 5)} minutes")
                    st.markdown(f"**Student Level:** {question.get('student_level', 'Intermediate')}")
                    
                    if question['question_type'] == "Multiple Choice" and 'options' in question:
                        st.markdown("**Options:**")
                        for option in question['options']:
                            st.markdown(f"- {option}")
                    
                    st.markdown("**Correct Answer:**")
                    st.markdown(question['correct_answer'])
                    
                    if 'explanation' in question:
                        st.markdown("**Explanation:**")
                        st.markdown(question['explanation'])
                    
                    if 'tags' in question:
                        st.markdown(f"**Tags:** {question['tags']}")
                    
                    # Button to save this question individually
                    save_button = st.button(f"Save Question {i+1} to Database", key=f"save_q_{i}")
                    
                    if save_button:
                        try:
                            # Create a new question object
                            new_question = Question(
                                chapter_id=selected_chapter_id[0],
                                content=question['question_content'],
                                difficulty=question['difficulty'],
                                estimated_time=question.get('estimated_time', 5),
                                student_level=question.get('student_level', 'Intermediate'),
                                tags=question.get('tags', ''),
                                question_type=question['question_type'],
                                correct_answer=question['correct_answer'],
                                explanation=question.get('explanation', ''),
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            
                            db.add(new_question)
                            db.commit()
                            
                            show_success(f"Question {i+1} saved successfully!")
                            
                        except Exception as e:
                            logger.error(f"Error saving question: {str(e)}")
                            show_error(f"Error saving question: {str(e)}")
            
            # Handle save all action
            if save_all:
                try:
                    # Set a flag in session state to indicate saving all
                    st.session_state.saving_all_questions = True
                    
                    # Store current chapter ID
                    st.session_state.save_chapter_id = selected_chapter_id[0]
                    
                    # Use st.rerun() instead of st.experimental_rerun()
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Error preparing to save all questions: {str(e)}")
                    show_error(f"Error: {str(e)}")
        
        # Handle saving all questions if flag is set
        if st.session_state.get("saving_all_questions"):
            try:
                saved_count = 0
                for question in st.session_state.generated_questions:
                    # Create a new question object
                    new_question = Question(
                        chapter_id=st.session_state.save_chapter_id,
                        content=question['question_content'],
                        difficulty=question['difficulty'],
                        estimated_time=question.get('estimated_time', 5),
                        student_level=question.get('student_level', 'Intermediate'),
                        tags=question.get('tags', ''),
                        question_type=question['question_type'],
                        correct_answer=question['correct_answer'],
                        explanation=question.get('explanation', ''),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.add(new_question)
                    saved_count += 1
                
                db.commit()
                show_success(f"All {saved_count} questions saved successfully!")
                
                # Reset flags and clear generated questions
                st.session_state.saving_all_questions = False
                st.session_state.generated_questions = []
                
            except Exception as e:
                logger.error(f"Error saving all questions: {str(e)}")
                show_error(f"Error saving all questions: {str(e)}")
                st.session_state.saving_all_questions = False
    
    except Exception as e:
        logger.error(f"Error in question generator: {str(e)}")
        show_error(f"Error: {str(e)}")

# For backward compatibility - this will be called when the file is run directly
if __name__ == "__main__":
    st.title("AI Question Generator")
    show_question_generator() 