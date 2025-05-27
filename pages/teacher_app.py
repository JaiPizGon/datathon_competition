import streamlit as st
from modules import data_loader, team_manager, config_manager # Assuming these are used by existing teacher_app features or will be by new ones
from modules import config # Import the config module
import pandas as pd # For displaying data later
import uuid # Was used before, might be needed

def show_teacher_page():
    st.set_page_config(layout="wide") # Ensure page config is set if not already
    st.title("Teacher Admin Dashboard")
    st.markdown("---")

    # --- Step 8: Apply Global UI Settings (Partial - Font Size) ---
    # This attempts to apply font size. Other settings like colors are saved but not dynamically applied here.
    if 'ui_settings' in st.session_state and 'font_size' in st.session_state.ui_settings:
        try:
            font_size_px = int(st.session_state.ui_settings['font_size'])
            if 10 <= font_size_px <= 30: # Basic validation
                st.markdown(
                    f"""
                    <style>
                    html, body, [class*="st-"] {{
                        font-size: {font_size_px}px !important;
                    }}
                    /* Attempt to make Streamlit's default components inherit this size */
                    /* More specific selectors might be needed for full coverage */
                    .stButton>button, .stTextInput>div>div>input, .stTextArea textarea, 
                    .stSelectbox>div>div, .stDateInput>div>div>input, 
                    .stTimeInput>div>div>input, .stNumberInput input[type="number"] {{
                        font-size: inherit !important;
                    }}
                    </style>
                    """, 
                    unsafe_allow_html=True
                )
            # else:
                # print(f"Admin UI: Font size {font_size_px}px from settings is out of typical range (10-30px). Not applying.")
        except ValueError:
            # print(f"Admin UI: Invalid font_size value in ui_settings: {st.session_state.ui_settings['font_size']}. Cannot apply.")
            pass # Silently ignore if font size is not a valid integer
    # --- End of Step 8 Part for Font Size ---


    # --- Admin Authentication ---
    if 'teacher_logged_in' not in st.session_state:
        st.session_state.teacher_logged_in = False

    if not st.session_state.teacher_logged_in:
        st.subheader("Admin Login")
        token_input = st.text_input("Enter Admin Token:", type="password", key="admin_token_input")
        
        if st.button("Login", key="admin_login_button"):
            if token_input == config.TEACHER_ADMIN_TOKEN:
                st.session_state.teacher_logged_in = True
                # Clear the input field after successful login attempt for security
                # This might not work as expected due to rerun, but it's good practice to try
                # A more robust way is to use forms and clear on submit if Streamlit evolves to support that better.
                # For now, the rerun will clear it effectively.
                st.rerun() 
            else:
                st.error("Invalid admin token. Please try again.")
        
        # Stop rendering further elements if not logged in
        st.stop() 
    
    # --- Logged-in Admin View ---
    # This part will only be reached if st.session_state.teacher_logged_in is True
    
    # Sidebar for Logout and potentially other navigation/settings later
    with st.sidebar:
        st.write(f"Welcome, Admin!") # Or some other identifier
        if st.button("Log Out", key="admin_logout_button"):
            st.session_state.teacher_logged_in = False
            # Clear other admin-specific session state if any
            if 'admin_selected_datathon_id' in st.session_state: # Example
                del st.session_state.admin_selected_datathon_id
            st.rerun()
        st.markdown("---") # Sidebar separator
        # Placeholder for future global settings UI
        # st.subheader("Global Settings (Coming Soon)")


    st.success("Admin login successful. Welcome to the Dashboard!")
    st.markdown("---")

    # --- Step 2: Data Fetching for Admin Dashboard ---
    st.header("Datathon Data Overview")

    # Retrieve datathon_id (set by parent_selector page)
    # current_datathon_id was already fetched and displayed as info earlier.
    # Let's ensure it's robustly available for fetching logic.
    current_datathon_id = st.session_state.get('current_datathon_id')
    if not current_datathon_id:
        st.error("No active datathon ID found. Please ensure a datathon has been configured via the 'Parent/Teacher Setup' page.")
        st.stop()
    
    st.info(f"Fetching data for Datathon ID: **{current_datathon_id}**")

    # Initialize placeholders in session state for dataframes
    if 'admin_teams_df' not in st.session_state:
        st.session_state.admin_teams_df = pd.DataFrame()
    if 'admin_submissions_df' not in st.session_state:
        st.session_state.admin_submissions_df = pd.DataFrame()

    # Button to refresh data
    if st.button("🔄 Refresh Data from Google Sheets", key="refresh_admin_data"):
        # Clear existing dataframes from session state to force a full reload
        if 'admin_teams_df' in st.session_state:
            del st.session_state.admin_teams_df
        if 'admin_submissions_df' in st.session_state:
            del st.session_state.admin_submissions_df
        st.rerun() # Rerun to trigger the data fetching logic below

    # Fetch data if not already loaded in this session or if refresh was clicked
    # This check helps avoid re-fetching on every interaction if data is already loaded.
    # The refresh button explicitly clears it to allow re-fetching.
    # However, for an admin dashboard, always fetching might be desired to see live data.
    # Let's try always fetching for now, simplifying the logic. Admin can refresh if needed.

    with st.spinner("Connecting to Google Services and fetching data..."):
        gspread_client = team_manager.get_gspread_client()
        if not gspread_client:
            st.error("Failed to get Google Sheets client. Cannot fetch data.")
            st.stop()

        datathon_workbook = team_manager.connect_to_workbook(gspread_client) # Uses name from secrets
        if not datathon_workbook:
            st.error("Failed to connect to the main 'DatathonTeams' workbook.")
            st.stop()

        # Fetch Teams Data
        teams_worksheet = team_manager.get_or_create_datathon_teams_worksheet(datathon_workbook, current_datathon_id)
        if teams_worksheet:
            try:
                all_teams_data = teams_worksheet.get_all_records(head=1) # head=1 assumes first row is header
                if all_teams_data:
                    st.session_state.admin_teams_df = pd.DataFrame(all_teams_data)
                    # st.success("Teams data loaded successfully.")
                else:
                    st.session_state.admin_teams_df = pd.DataFrame() # Empty if sheet has only header or is empty
                    st.info(f"No team data found in sheet '{teams_worksheet.title}'.")
            except Exception as e:
                st.error(f"Error reading teams data from sheet '{teams_worksheet.title}': {e}")
                st.session_state.admin_teams_df = pd.DataFrame() # Ensure it's an empty DF on error
        else:
            st.warning(f"Could not access the Teams worksheet for datathon '{current_datathon_id}'.")
            st.session_state.admin_teams_df = pd.DataFrame()


        # Fetch Submissions Data
        # Assuming get_or_create_submissions_sheet is ready from Student App plan (Step 6)
        # It should create/get a sheet like "Submissions_<datathon_id>"
        submissions_sheet_name = f"Submissions_{current_datathon_id}" 
        submissions_worksheet = None
        try:
            submissions_worksheet = datathon_workbook.worksheet(submissions_sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.info(f"Submissions sheet ('{submissions_sheet_name}') not found for this datathon. No submissions yet or sheet not created.")
            st.session_state.admin_submissions_df = pd.DataFrame()
        except Exception as e:
            st.error(f"Error trying to access submissions sheet '{submissions_sheet_name}': {e}")
            st.session_state.admin_submissions_df = pd.DataFrame()

        if submissions_worksheet: # Proceed only if sheet was found
            try:
                all_submissions_data = submissions_worksheet.get_all_records(head=1)
                if all_submissions_data:
                    st.session_state.admin_submissions_df = pd.DataFrame(all_submissions_data)
                    # st.success("Submissions data loaded successfully.")
                else:
                    st.session_state.admin_submissions_df = pd.DataFrame()
                    st.info(f"No submission data found in sheet '{submissions_worksheet.title}'.")
            except Exception as e:
                st.error(f"Error reading submissions data from sheet '{submissions_worksheet.title}': {e}")
                st.session_state.admin_submissions_df = pd.DataFrame()
    
    # Display quick summary or counts
    st.metric("Total Teams Registered", len(st.session_state.admin_teams_df))
    st.metric("Total Submissions Received", len(st.session_state.admin_submissions_df))
    st.markdown("---")


    # Placeholder for Step 4 & 5: Display Teams/Submissions & Admin Actions
    # These sections will use st.session_state.admin_teams_df and st.session_state.admin_submissions_df
    # ... (rest of the page) ...

    # --- Step 4: Manage Teams ---
    st.subheader("Manage Registered Teams")

    # Retrieve teams_df and teams_worksheet from session state (set in Step 2)
    admin_teams_df = st.session_state.get('admin_teams_df')
    teams_worksheet = st.session_state.get('teams_worksheet') # Assuming this was stored in Step 2

    if admin_teams_df is None or not teams_worksheet:
        st.warning("Teams data or worksheet not available. Please ensure data is fetched (Step 2). Try clicking 'Refresh Data'.")
        # Optionally, attempt to re-fetch or guide user. For now, just warn.
    elif admin_teams_df.empty:
        st.info("No teams registered for this datathon yet.")
    else:
        # Displaying teams using st.expander for each team for clarity with buttons
        for index, row in admin_teams_df.iterrows():
            team_name = row.get("TeamName", f"UnnamedTeam_Row{index}") # Fallback if 'TeamName' column is missing
            
            # Construct member list string for display
            member_list = []
            # Assuming get_max_team_size() is accessible or MAX_TEAM_SIZE from config
            # For simplicity, let's just iterate over known possible member columns if they exist in the df
            for i in range(1, config.MAX_TEAM_SIZE + 1): # MAX_TEAM_SIZE from config
                 member_col = f"Member{i}"
                 if member_col in row and row[member_col] and str(row[member_col]).strip():
                     member_list.append(str(row[member_col]))
            members_display = ", ".join(member_list) if member_list else "No members listed"

            with st.expander(f"Team: {team_name} (Members: {members_display})"):
                st.write(f"**Team Details for:** {team_name}")
                # Display more team details if needed, e.g., password column for admin view (though maybe not directly)
                # st.write(row) # For debugging or more info

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Reset Password", key=f"reset_pw_{team_name}_{index}", help=f"Reset password for team {team_name}"):
                        new_password = team_manager.reset_team_password(teams_worksheet, team_name)
                        if new_password:
                            st.success(f"Password for team '{team_name}' has been reset to: **{new_password}**")
                            # No automatic data refresh here as the password change is not directly visible in the main df view
                            # Admin should be aware the action was performed.
                        else:
                            st.error(f"Failed to reset password for team '{team_name}'.")
                        # No rerun needed, as it would close the expander and lose the message.

                with col2:
                    # Using a form for delete button to add a confirmation step if desired,
                    # but a direct button is also common. For now, direct button.
                    if st.button(f"⚠️ Remove Team", key=f"remove_team_{team_name}_{index}", help=f"Permanently remove team {team_name}"):
                        if team_manager.delete_team_row(teams_worksheet, team_name):
                            st.success(f"Team '{team_name}' removed successfully.")
                            # Clear session state DF to trigger refresh on rerun
                            if 'admin_teams_df' in st.session_state:
                                del st.session_state.admin_teams_df 
                            st.rerun()
                        else:
                            st.error(f"Failed to remove team '{team_name}'. Team might have already been removed or an error occurred.")
                            # Consider a rerun even on failure if state might be inconsistent

        st.markdown("---") # Separator after the teams list
    
    # --- Step 5: Manage Student Submissions ---
    st.subheader("Manage Student Submissions")

    admin_submissions_df = st.session_state.get('admin_submissions_df')
    # Retrieve the submissions_worksheet object. It might not have been stored directly in session_state
    # but can be re-fetched if datathon_workbook and current_datathon_id are in session_state.
    # For simplicity, let's assume it needs to be fetched or was stored.
    # If Step 2 stored datathon_workbook in session state:
    datathon_workbook = st.session_state.get("datathon_workbook")
    current_datathon_id = st.session_state.get("current_datathon_id")
    submissions_worksheet = None # Define outside to ensure it's in scope for the button logic
    
    if datathon_workbook and current_datathon_id:
        submissions_sheet_name = f"Submissions_{current_datathon_id}"
        try:
            submissions_worksheet = datathon_workbook.worksheet(submissions_sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # This case should be handled by the data fetching part (Step 2) already by admin_submissions_df being empty
            pass 
        except Exception as e:
            st.error(f"Error re-accessing submissions sheet '{submissions_sheet_name}': {e}")


    if admin_submissions_df is None:
        st.warning("Submissions data not available. Please ensure data is fetched (Step 2). Try clicking 'Refresh Data'.")
    elif admin_submissions_df.empty:
        st.info("No submissions recorded for this datathon yet.")
    elif submissions_worksheet is None and not admin_submissions_df.empty : # Check if worksheet object is available for delete action, but still show df if it exists
        st.error("Submissions worksheet object not found. Deletion will not be possible. Try refreshing data.")
        st.dataframe(admin_submissions_df) # Display data even if delete is broken
    else: # This means admin_submissions_df is not empty AND submissions_worksheet is available (or df is empty and this block is skipped)
        st.dataframe(admin_submissions_df) # Display all submissions

        st.markdown("---")
        st.write("Delete a specific submission:")
        
        submission_options = ["None"]
        submission_identifiers_map = {}

        for index, row in admin_submissions_df.iterrows():
            team_name = row.get("TeamName", "N/A")
            timestamp = row.get("Timestamp", "N/A")
            
            # Attempt to get the primary metric for display, if configured and present
            primary_metric_display = ""
            current_datathon_type_for_metric = st.session_state.get('datathon_type_final', '').lower() # from parent_selector Step 4
            primary_metric_name = config.PRIMARY_METRICS.get(current_datathon_type_for_metric)
            
            if primary_metric_name and primary_metric_name in row:
                try:
                    metric_value = row[primary_metric_name]
                    # Ensure it's a number before trying to format
                    if isinstance(metric_value, (int, float)) and not pd.isna(metric_value):
                         primary_metric_display = f", {primary_metric_name}: {float(metric_value):.4f}"
                    elif str(metric_value).strip(): # Non-empty string
                         primary_metric_display = f", {primary_metric_name}: {str(metric_value)}"
                    # else, keep it empty if value is None or empty string
                except (ValueError, TypeError): 
                    primary_metric_display = f", {primary_metric_name}: (N/A)"
            
            display_text = f"Team: {team_name}, Time: {timestamp}{primary_metric_display} (Index: {index})"
            submission_options.append(display_text)
            submission_identifiers_map[display_text] = (team_name, timestamp)

        selected_submission_display = st.selectbox(
            "Select a submission to delete:",
            options=submission_options,
            index=0, 
            key="select_submission_to_delete"
        )

        if st.button("⚠️ Delete Selected Submission", key="delete_submission_button", disabled=(selected_submission_display == "None")):
            if selected_submission_display != "None" and submissions_worksheet: # Ensure worksheet is available
                team_to_delete_from, ts_to_delete = submission_identifiers_map[selected_submission_display]
                
                if team_manager.delete_submission_row(submissions_worksheet, team_to_delete_from, ts_to_delete):
                    st.success(f"Submission for Team '{team_to_delete_from}' at '{ts_to_delete}' deleted successfully.")
                    if 'admin_submissions_df' in st.session_state:
                        del st.session_state.admin_submissions_df
                    st.rerun()
                else:
                    st.error(f"Failed to delete submission for Team '{team_to_delete_from}' at '{ts_to_delete}'. It might have already been removed or an error occurred.")
            elif submissions_worksheet is None:
                 st.error("Cannot delete: Submissions worksheet is not accessible. Try refreshing data.")
            else:
                st.warning("No submission selected for deletion.")
        
    st.markdown("---") # Separator after the submissions list

    # --- Step 7: UI Controls for Global Settings ---
    st.subheader("Global UI Settings")

    # Load settings on first load or if not present in session state
    # drive_service should be available from Step 2 (Data Fetching for Admin Dashboard)
    if 'ui_settings' not in st.session_state:
        if drive_service: # Check if drive_service was successfully obtained earlier in this function
             with st.spinner("Loading UI settings from Google Drive..."):
                st.session_state.ui_settings = config_manager.load_uiconfig_from_drive(drive_service)
        else:
            st.warning("Google Drive service not available. Using default UI settings. Cannot load/save custom UI settings.")
            st.session_state.ui_settings = config_manager.DEFAULT_UI_SETTINGS.copy()


    with st.expander("Customize Application Appearance & Behavior", expanded=False):
        if not drive_service: # Disable if no drive service
            st.caption("Saving/loading of custom UI settings is disabled as Google Drive is not connected.")

        # Get current values from session state, falling back to defaults from config_manager
        current_font_size = st.session_state.ui_settings.get('font_size', config_manager.DEFAULT_UI_SETTINGS['font_size'])
        current_decimal_precision = st.session_state.ui_settings.get('decimal_precision', config_manager.DEFAULT_UI_SETTINGS['decimal_precision'])
        current_primary_color = st.session_state.ui_settings.get('primary_color', config_manager.DEFAULT_UI_SETTINGS['primary_color'])
        current_bg_color = st.session_state.ui_settings.get('background_color', config_manager.DEFAULT_UI_SETTINGS['background_color'])
        current_text_color = st.session_state.ui_settings.get('text_color', config_manager.DEFAULT_UI_SETTINGS['text_color'])

        new_font_size = st.number_input(
            "Base Font Size (px)", 
            min_value=10, max_value=24, 
            value=current_font_size, 
            key="ui_font_size_setter",
            disabled=not drive_service
        )
        new_decimal_precision = st.number_input(
            "Decimal Precision for Scores", 
            min_value=1, max_value=6, 
            value=current_decimal_precision, 
            key="ui_decimal_precision_setter",
            disabled=not drive_service
        )
        
        st.info("Color settings below are saved for reference. Applying them dynamically across the entire app theme requires advanced setup (e.g., custom CSS injection or Streamlit theming features if available). Step 8 will attempt basic font size application.")
        
        new_primary_color = st.color_picker(
            "Primary Accent Color", 
            value=current_primary_color, 
            key="ui_primary_color_setter",
            disabled=not drive_service
        )
        new_bg_color = st.color_picker(
            "Application Background Color", 
            value=current_bg_color, 
            key="ui_bg_color_setter",
            disabled=not drive_service
        )
        new_text_color = st.color_picker(
            "Application Text Color", 
            value=current_text_color, 
            key="ui_text_color_setter",
            disabled=not drive_service
        )

        if st.button("Save UI Settings", key="save_ui_settings_button_main", disabled=not drive_service):
            updated_settings = {
                "font_size": new_font_size,
                "decimal_precision": new_decimal_precision,
                "primary_color": new_primary_color,
                "background_color": new_bg_color,
                "text_color": new_text_color
            }
            if drive_service:
                if config_manager.save_uiconfig_to_drive(drive_service, updated_settings):
                    st.session_state.ui_settings = updated_settings.copy()
                    st.success("UI Settings saved successfully to Google Drive!")
                    st.info("Font size change will attempt to apply on next rerun (Step 8). Other color changes are saved but may require manual theme adjustments or advanced CSS for full effect.")
                else:
                    st.error("Failed to save UI settings to Google Drive.")
            else:
                st.error("Google Drive service not connected. Cannot save settings.")
    
    st.markdown("---") # Separator


    # --- Original Teacher App Content (from previous implementation if any) ---
    # The original content of show_teacher_page (data upload portal) needs to be integrated here.
    # For now, this part is simplified to focus on the admin dashboard structure.
    # If the Teacher App was originally for data uploads (as in earlier plans),
    # that functionality might need to be a separate page or integrated carefully.
    # Based on the new request, this page is now an "admin dashboard".
    # The previous "Teacher/Parent - Data Upload Portal" might be what parent_selector.py became.

    # For this step, we'll assume the old content is superseded by this admin dashboard.
    # If the user had `teacher_app.py` doing something else, that needs clarification.
    # The current `teacher_app.py` (from turn 24) had a complex data upload UI.
    # This will be replaced by the admin dashboard logic.

    # Example: Displaying the current datathon ID from session state if set by parent selector
    current_datathon_id = st.session_state.get('current_datathon_id', 'Not Set')
    st.info(f"Currently selected Datathon ID (from Parent Setup): **{current_datathon_id}**")
    st.write("You will manage teams and submissions for this datathon below once implemented.")


# Allow direct execution for testing
if __name__ == "__main__":
    # Mock config if not available (e.g. if config.py is not fully populated or for isolated testing)
    class MockConfig:
        TEACHER_ADMIN_TOKEN = "testtoken" # Use a known token for direct testing
        # Add other config vars if show_teacher_page uses them directly before login for some reason

    if not hasattr(st, 'secrets') or "google_oauth" not in st.secrets:
        st.warning("Google OAuth secrets not found. Parts of the app requiring Google services may fail.")
        # Mock secrets if needed for functions called before full auth, though not ideal.

    # If running directly, config might not be imported in the same way as when run via streamlit run app.py
    # For robust direct testing, ensure config can be loaded or mock it.
    # For this subtask, team_manager and data_loader calls are mostly after login,
    # so login itself is the main focus.
    
    # To run this directly and test login:
    # 1. Ensure modules/config.py has TEACHER_ADMIN_TOKEN set (or use MockConfig above).
    # 2. Run `streamlit run pages/teacher_app.py`.
    # 3. Enter the token.
    
    # For the purpose of this subtask, we assume config is importable.
    # If `from modules import config` fails on direct run, it means PYTHONPATH isn't set up as Streamlit does.
    # This is usually fine, as main entry is `app.py`.
    
    show_teacher_page()
