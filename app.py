import streamlit as st
from pages import parent_selector, student_app, teacher_app
from modules import data_loader, team_manager, config_manager # Added imports

# --- Step 6: Initial Page Configuration ---
# This should be the very first Streamlit command in the app.py script, except for imports.
st.set_page_config(
    page_title="Datathon Hub",
    page_icon="🏆",  # Optional: Add a fun emoji or path to a .ico file
    layout="wide",
    initial_sidebar_state="expanded",
    # menu_items={ # Optional: Add custom menu items
    #     'Get Help': 'https://www.example.com/help',
    #     'Report a bug': "https://www.example.com/bug",
    #     'About': "# This is the Datathon Hub!"
    # }
)
# --- End of Step 6 ---

def main():
    # --- Step 2: Global Google API Authentication on Load ---
    # Initialize session state flags if they don't exist
    if 'drive_service_initialized' not in st.session_state:
        st.session_state.drive_service_initialized = False
    if 'gspread_client_initialized' not in st.session_state:
        st.session_state.gspread_client_initialized = False
    if 'global_auth_attempted' not in st.session_state: # To run this block once per session effectively
        st.session_state.global_auth_attempted = False


    # Attempt global authentication only once per session or if not yet successful
    # The individual get_..._service/client functions handle their own credential state.
    # Calling them here ensures they are triggered early if needed.
    if not st.session_state.drive_service_initialized or not st.session_state.gspread_client_initialized:
        # Using a general spinner for the initial auth attempt.
        # Individual functions will show their specific auth links if needed.
        with st.spinner("Connecting to Google services... Please follow authentication prompts if they appear."):
            drive_service = data_loader.get_drive_service()
            if drive_service:
                st.session_state.drive_service_initialized = True
                st.session_state.drive_service = drive_service # Store the service object itself
                # Optional: st.sidebar.success("Drive Connected", icon="✅") # Can be noisy
            else:
                # get_drive_service() itself should render messages/auth links.
                # If it returns None, it means auth is pending or failed.
                # No specific error needed here unless we want to halt the whole app.
                pass

            gspread_client = team_manager.get_gspread_client()
            if gspread_client:
                st.session_state.gspread_client_initialized = True
                st.session_state.gspread_client = gspread_client # Store the client object
                # Optional: st.sidebar.success("Sheets Connected", icon="✅")
            else:
                # get_gspread_client() handles its own UI for auth.
                pass
        
        # If either service is still not initialized after attempting, it means user interaction for OAuth is pending.
        # The respective service getter functions will display the necessary links/prompts when called by pages.
        # This initial call just brings the prompt forward if no valid tokens are found.
    
    # --- End of Step 2 ---

    # --- Step 4: Global UI Settings Application - Part 1: Load Config & Apply Font ---
    if 'ui_settings' not in st.session_state: # Load once per session or if not already loaded
        # Retrieve drive_service from session state (set in Step 2)
        drive_service_global = st.session_state.get('drive_service')
        if drive_service_global:
            with st.spinner("Loading UI preferences..."):
                st.session_state.ui_settings = config_manager.load_uiconfig_from_drive(drive_service_global)
        else:
            # If drive_service isn't up yet (e.g., user hasn't authed Drive)
            # still initialize ui_settings with defaults so app doesn't break.
            # Teacher App might later load them again if Drive auth completes there.
            st.session_state.ui_settings = config_manager.DEFAULT_UI_SETTINGS.copy()
            # Optionally, add a warning if Drive isn't connected yet for UI settings
            # if not st.session_state.get('drive_service_initialized'):
            #     st.sidebar.warning("UI settings from Drive require Google Drive connection.")


    # Apply Font Size Globally
    # This should run on each rerun to ensure font is applied if settings change and page reruns.
    # (Though changing settings in teacher_app and seeing it here requires a full app rerun or callback)
    try:
        font_size_px = int(st.session_state.ui_settings.get('font_size', config_manager.DEFAULT_UI_SETTINGS['font_size']))
        if 10 <= font_size_px <= 30: # Basic validation
            st.markdown(
                f"""
                <style>
                html, body, [class*="st-"] {{
                    font-size: {font_size_px}px !important;
                }}
                </style>
                """, 
                unsafe_allow_html=True
            )
    except (ValueError, TypeError):
        # Silently use default if font_size is invalid in settings
        pass 
    # --- End of Step 4 ---

    # --- Navigation (existing code from Step 1 review) ---
    st.sidebar.title("Navigation")
    if "page" not in st.session_state:
        st.session_state.page = "Parent/Teacher Setup" 

    PAGES = {
        "Parent/Teacher Setup": parent_selector.show_parent_selector_page,
        "Student App": student_app.show_student_page,
        "Teacher App": teacher_app.show_teacher_page
    }
    st.session_state.page = st.sidebar.radio(
        "Go to", list(PAGES.keys()), 
        index=list(PAGES.keys()).index(st.session_state.page)
    )
    
    # --- Placeholder for Step 4: Global UI Settings Application (Config Load & Font) ---
    # This will come after auth but before rendering the selected page.
    # For now, just a comment.
    # apply_global_ui_settings() # Conceptual function call

    # Display the selected page
    page_function = PAGES[st.session_state.page]
    
    # Before calling page_function, ensure services are available if page needs them.
    # The pages themselves also call the getters, which now first check session_state.
    # This makes the app more resilient if global auth is interrupted.
    if st.session_state.page == "Parent/Teacher Setup":
        if not st.session_state.drive_service_initialized: # Example check
             st.warning("Google Drive connection is pending. Some features might be unavailable until authenticated.")
        # Parent Selector also needs Sheets for team aspects eventually, but primarily Drive for datasets
    elif st.session_state.page == "Student App" or st.session_state.page == "Teacher App":
        if not st.session_state.drive_service_initialized or not st.session_state.gspread_client_initialized:
            st.warning("Google Drive or Sheets connection is pending. Some features might be unavailable until authenticated.")
            
    page_function()

if __name__ == "__main__":
    main()
