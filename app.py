import streamlit as st
from pages import parent_selector, student_app, teacher_app

def main():
    st.sidebar.title("Navigation")
    
    # Initialize session state for page if not present
    if "page" not in st.session_state:
        st.session_state.page = "Parent/Teacher Setup" # Default page

    # Define pages
    PAGES = {
        "Parent/Teacher Setup": parent_selector.show_parent_selector_page,
        "Student App": student_app.show_student_page,
        "Teacher App": teacher_app.show_teacher_page
    }

    # Sidebar navigation
    # Use st.session_state.page to keep selection upon rerun
    st.session_state.page = st.sidebar.radio(
        "Go to", 
        list(PAGES.keys()), 
        index=list(PAGES.keys()).index(st.session_state.page) # Set index based on current page in session_state
    )
    
    # Display the selected page
    page_function = PAGES[st.session_state.page]
    page_function()

if __name__ == "__main__":
    main()
