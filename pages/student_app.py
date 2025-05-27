import streamlit as st
from modules import data_loader, team_manager, metrics, config, config_manager # Assuming these modules exist and have the required functions
import pandas as pd # Will be needed later

def show_student_page():
    st.set_page_config(layout="wide")
    st.title("Student Datathon Portal")
    st.markdown("---")

    # --- 0. Load Datathon Configuration ---
    # Attempt to retrieve datathon_id from session state (set by parent_selector)
    # Using st.session_state.get to avoid KeyError if not set
    datathon_name = st.session_state.get('datathon_train_file_name', None) 
    datathon_id = None
    if datathon_name:
        # Create a more robust datathon_id, e.g., by removing extensions and sanitizing
        datathon_id = datathon_name.split('.')[0].replace(" ", "_").lower()
        st.session_state.current_datathon_id = datathon_id # Store for consistent use
        st.caption(f"Current Datathon Event ID: `{datathon_id}` (Based on training data: {datathon_name})")
    else:
        st.error("Datathon has not been configured by the Parent/Teacher yet. Please ask them to set up a datathon in the 'Parent/Teacher Setup' page.")
        st.stop()
    
    st.markdown("---")

    # --- 1. Authenticate Google Services ---
    st.header("Connecting to Google Services...")
    
    # Get Google Drive Service
    drive_service = data_loader.get_drive_service()
    if not drive_service:
        st.warning("Google Drive authentication failed or is pending. Please complete the authentication process if prompted.")
        # data_loader.get_drive_service() handles showing the auth link/input
        st.stop()
    # st.success("Connected to Google Drive successfully!") # Optional: Can make UI noisy

    # Get Google Sheets Service (gspread client)
    gspread_client = team_manager.get_gspread_client()
    if not gspread_client:
        st.warning("Google Sheets authentication failed or is pending. Please complete the authentication process if prompted.")
        # team_manager.get_gspread_client() handles showing the auth link/input
        st.stop()
    # st.success("Connected to Google Sheets successfully!") # Optional

    # Connect to the main "DatathonTeams" workbook
    # The connect_to_workbook function in team_manager now gets name from st.secrets
    datathon_workbook = team_manager.connect_to_workbook(gspread_client)
    if not datathon_workbook:
        st.error("Failed to connect to the 'DatathonTeams' workbook. Ensure it's shared correctly and named as per configuration in secrets.toml.")
        st.stop()
    # st.success(f"Connected to workbook: '{datathon_workbook.title}'") # Optional

    # Get/Create the specific worksheet for this datathon's teams
    # This uses the datathon_id derived from the training set name
    teams_worksheet = team_manager.get_or_create_datathon_teams_worksheet(datathon_workbook, datathon_id)
    if not teams_worksheet:
        st.error(f"Failed to get or create the specific 'Teams' worksheet for datathon '{datathon_id}'.")
        st.stop()
    # st.success(f"Using team sheet: '{teams_worksheet.title}' within '{datathon_workbook.title}'") # Optional
    
    st.success("All Google services connected and datathon sheets ready!")
    st.markdown("---")

    # Store worksheet objects in session state for other functions on this page to use
    st.session_state.teams_worksheet = teams_worksheet
    st.session_state.datathon_workbook = datathon_workbook # Might be needed for submissions sheet later

    # --- Placeholder for Step 2: Team Login/Join UI ---
    # (This code replaces the placeholder for Step 2 in show_student_page)

        # --- Step 2: Team Login / Join UI ---
        st.header("Step 2: Create or Join a Team")

        # Initialize session state variables if they don't exist
        if 'student_logged_in' not in st.session_state:
            st.session_state.student_logged_in = False
        if 'student_team_name' not in st.session_state:
            st.session_state.student_team_name = None
        if 'student_id' not in st.session_state: # For the student's own ID/email
            st.session_state.student_id = "" 
        if 'is_team_leader' not in st.session_state:
            st.session_state.is_team_leader = False
        
        # Retrieve teams_worksheet from session state (should have been set in Step 1)
        teams_worksheet = st.session_state.get('teams_worksheet')
        if not teams_worksheet:
            st.error("Team management sheet not available. Cannot proceed with login/join. Please ensure Step 1 completed successfully.")
            st.stop()

        if st.session_state.student_logged_in:
            st.success(f"You are logged in as **{st.session_state.student_id}** in Team: **{st.session_state.student_team_name}**.")
            if st.button("Log Out"):
                st.session_state.student_logged_in = False
                st.session_state.student_team_name = None
                st.session_state.student_id = "" # Clear student ID as well
                st.session_state.is_team_leader = False
                # Clear other session state related to student's specific submission if any
                if 'submission_successful' in st.session_state:
                    del st.session_state.submission_successful
                if 'calculated_metrics' in st.session_state:
                    del st.session_state.calculated_metrics
                st.rerun()
        else:
            create_tab, join_tab = st.tabs(["Create New Team", "Join Existing Team"])

            with create_tab:
                st.subheader("Create a New Team")
                with st.form("create_team_form"):
                    new_team_name = st.text_input("Choose a Team Name:", key="create_team_name")
                    creator_student_id = st.text_input("Your Student ID/Email (this will be Member 1):", key="creator_id", value=st.session_state.student_id)
                    submitted_create = st.form_submit_button("Create Team")

                    if submitted_create:
                        if not new_team_name.strip():
                            st.error("Team Name cannot be empty.")
                        elif not creator_student_id.strip():
                            st.error("Your Student ID/Email cannot be empty.")
                        else:
                            st.session_state.student_id = creator_student_id # Store entered ID
                            result = team_manager.create_new_team(teams_worksheet, new_team_name, creator_student_id)
                            if result:
                                team_name_created, password_created = result
                                st.session_state.student_logged_in = True
                                st.session_state.student_team_name = team_name_created
                                # student_id already set from input
                                st.session_state.is_team_leader = True
                                st.success(f"Team '{team_name_created}' created successfully!")
                                st.info(f"IMPORTANT: Your new team password is: **{password_created}**. Share this with your teammates to join.")
                                st.balloons()
                                st.rerun() # Rerun to reflect logged-in state
                            else:
                                # Error message already shown by create_new_team if team exists or other issues
                                pass # team_manager function already shows st.error/warning

            with join_tab:
                st.subheader("Join an Existing Team")
                with st.form("join_team_form"):
                    existing_team_name = st.text_input("Team Name to Join:", key="join_team_name")
                    team_password = st.text_input("Team Password:", type="password", key="join_team_password")
                    joiner_student_id = st.text_input("Your Student ID/Email:", key="joiner_id", value=st.session_state.student_id)
                    submitted_join = st.form_submit_button("Join Team")

                    if submitted_join:
                        if not existing_team_name.strip():
                            st.error("Team Name cannot be empty.")
                        elif not team_password: # Password can be anything, so just check if empty
                            st.error("Password cannot be empty.")
                        elif not joiner_student_id.strip():
                            st.error("Your Student ID/Email cannot be empty.")
                        else:
                            st.session_state.student_id = joiner_student_id # Store entered ID
                            joined = team_manager.join_team(teams_worksheet, existing_team_name, team_password, joiner_student_id)
                            if joined:
                                st.session_state.student_logged_in = True
                                st.session_state.student_team_name = existing_team_name
                                # student_id already set from input
                                st.session_state.is_team_leader = False # Not leader if joining
                                st.success(f"Successfully joined team '{existing_team_name}'!")
                                st.balloons()
                                st.rerun() # Rerun to reflect logged-in state
                            else:
                                # Error message already shown by join_team
                                pass # team_manager function already shows st.error/warning
        
        st.markdown("---") # Separator after login/join section

    # --- Placeholder for Step 3: Post-Login UI (Download, Upload) ---
    # (This will be shown conditionally based on login state)
        # (This code should be placed after the "Step 2: Team Login / Join UI" st.markdown("---") )
        # It will be conditionally displayed based on login status.

        # --- Step 3: Datathon Participation (Post-Login) ---
        if st.session_state.get('student_logged_in', False):
            st.header(f"Welcome, Team: {st.session_state.student_team_name} (Student: {st.session_state.student_id})")
            st.markdown("---")

            # A. Download Test Dataset
            st.subheader("A. Download Test Data")
            test_inputs_file_id = st.session_state.get('datathon_test_inputs_file_id', None) # Set by parent_selector
            
            # Retrieve drive_service from session_state if stored, or call get_drive_service() again
            # Assuming drive_service is available in the scope of show_student_page() from Step 1
            # If not, it might need to be explicitly passed or retrieved from session state.
            # For this subtask, assume 'drive_service' variable from Step 1 is accessible.
            
            if test_inputs_file_id:
                with st.spinner("Fetching download link for test input data..."):
                    test_input_link = data_loader.get_drive_shareable_link(test_inputs_file_id, drive_service) # drive_service from Step 1
                if test_input_link:
                    st.markdown(f"**Download your test input data (CSV):** [{test_inputs_file_id}]({test_input_link})")
                    # Provide direct download button as well for convenience
                    # To do this, we'd need data_loader.download_csv_from_drive_to_dataframe then st.download_button
                    # For now, link is sufficient as per plan.
                else:
                    st.error("Could not retrieve a shareable link for the test input data. Please contact the admin.")
            else:
                st.warning("Test input data is not available or not configured for this datathon. Please contact the admin.")
            
            st.markdown("---")

            # B. Upload Predictions
            st.subheader("B. Upload Your Predictions")
            
            # Initialize session state for submission status if it doesn't exist
            if 'submission_successful' not in st.session_state:
                st.session_state.submission_successful = False
            if 'calculated_metrics' not in st.session_state:
                st.session_state.calculated_metrics = None

            # If a submission was just made, show metrics and a way to submit again
            if st.session_state.submission_successful and st.session_state.calculated_metrics:
                st.success("Your previous submission was successful!")
                st.write("Calculated Metrics:")
                # Display metrics in a more structured way if they are a dict
                if isinstance(st.session_state.calculated_metrics, dict):
                    for metric_name, metric_value in st.session_state.calculated_metrics.items():
                        st.metric(label=metric_name, value=f"{metric_value:.4f}") # Assuming metrics are float
                else:
                    st.write(st.session_state.calculated_metrics) # Fallback
                
                if st.button("Upload Another Prediction File"):
                    st.session_state.submission_successful = False
                    st.session_state.calculated_metrics = None
                    st.rerun() # Rerun to show the file uploader again
            
            # Show file uploader only if no successful submission is currently registered in session
            if not st.session_state.submission_successful:
                uploaded_prediction_file = st.file_uploader(
                    "Upload your prediction CSV file here.",
                    type=['csv'],
                    key="prediction_uploader"
                )
                
                # Add a submit button for processing the uploaded file
                # The actual processing logic (Step 5) will be triggered by this button.
                if st.button("Submit Predictions for Scoring", disabled=(uploaded_prediction_file is None)):
                    if uploaded_prediction_file is not None:
                        # Store uploaded file in session state for Step 5 to process
                        st.session_state.uploaded_prediction_file = uploaded_prediction_file
                        # Store uploaded file in session state for Step 5 to process
                        st.session_state.uploaded_prediction_file = uploaded_prediction_file
                        
                        with st.spinner("Processing your submission... Hang tight!"):
                            # --- Begin Submission Processing Logic (Step 5) ---
                            true_outputs_file_id = st.session_state.get('datathon_test_outputs_file_id')
                            datathon_type = st.session_state.get('datathon_type_final')
                            # drive_service should be in scope from Step 1 of show_student_page()

                            if not true_outputs_file_id:
                                st.error("True test output file ID is not configured for this datathon. Cannot score. Please contact admin.")
                                st.stop()
                            
                            df_true_outputs = data_loader.download_csv_from_drive_to_dataframe(drive_service, true_outputs_file_id)
                            if df_true_outputs is None or df_true_outputs.empty:
                                st.error(f"Could not load the true test output data from Drive (File ID: {true_outputs_file_id}). Please contact admin.")
                                st.stop()

                            try:
                                df_predictions = pd.read_csv(st.session_state.uploaded_prediction_file)
                            except Exception as e:
                                st.error(f"Error reading your uploaded prediction CSV: {e}")
                                st.stop()

                            if df_predictions.empty:
                                st.error("Your uploaded prediction file is empty.")
                                st.stop()

                            # Define expected column names (IMPORTANT ASSUMPTION - document this)
                            TARGET_COLUMN_NAME = 'Actual'  # Expected in true_outputs.csv
                            PREDICTION_COLUMN_NAME = 'Predicted' # Expected in student's submission.csv
                            
                            st.info(f"Scoring assumes your prediction file has a column named '{PREDICTION_COLUMN_NAME}' "
                                    f"and the true data has a target column named '{TARGET_COLUMN_NAME}'.")

                            if TARGET_COLUMN_NAME not in df_true_outputs.columns:
                                st.error(f"Missing target column '{TARGET_COLUMN_NAME}' in the true test output data. Contact admin.")
                                st.stop()
                            if PREDICTION_COLUMN_NAME not in df_predictions.columns:
                                st.error(f"Missing prediction column '{PREDICTION_COLUMN_NAME}' in your uploaded file.")
                                st.stop()
                            
                            if len(df_true_outputs) != len(df_predictions):
                                st.error(f"Row count mismatch: True outputs have {len(df_true_outputs)} rows, "
                                         f"your predictions have {len(df_predictions)} rows. Please ensure they match.")
                                st.stop()

                            calculated_metrics_dict = None
                            if datathon_type == "Regression":
                                calculated_metrics_dict = metrics.calculate_regression_metrics(df_true_outputs, df_predictions, TARGET_COLUMN_NAME, PREDICTION_COLUMN_NAME)
                            elif datathon_type == "Classification":
                                calculated_metrics_dict = metrics.calculate_classification_metrics(df_true_outputs, df_predictions, TARGET_COLUMN_NAME, PREDICTION_COLUMN_NAME)
                            elif datathon_type == "Forecasting":
                                calculated_metrics_dict = metrics.calculate_forecasting_metrics(df_true_outputs, df_predictions, TARGET_COLUMN_NAME, PREDICTION_COLUMN_NAME)
                            elif datathon_type == "SARIMA": 
                                calculated_metrics_dict = metrics.calculate_sarima_metrics(df_true_outputs, df_predictions, TARGET_COLUMN_NAME, PREDICTION_COLUMN_NAME)
                            else:
                                st.error(f"Unsupported datathon type '{datathon_type}' for scoring.")
                                st.stop()

                            if calculated_metrics_dict:
                                st.session_state.calculated_metrics = calculated_metrics_dict
                                st.session_state.submission_successful = True
                            else:
                                st.error("Metrics calculation failed. Check the console logs in `modules/metrics.py` for more details if you are the admin, or ensure your data format is correct.")
                                st.session_state.submission_successful = False
                                st.session_state.calculated_metrics = None
                            # --- End Submission Processing Logic (Step 5) ---
                        st.rerun() # Rerun to display metrics or error messages and update UI state
                    
                    #This elif handles the case where the button was clicked without a file (if we were tracking button clicks separately)
                    #For now, the button disabled state handles this, but if that changed, this would be a fallback.
                    # elif uploaded_prediction_file is None and st.session_state.get('submit_predictions_button_clicked', False): 
                    #     st.warning("Please upload a prediction file first.")
                    #     st.session_state.submit_predictions_button_clicked = False # Reset flag
            
            st.markdown("---")
        # else:
            # This part is implicitly handled: if not logged in, this whole section doesn't show.
            # st.info("Please log in or create a team to participate.")

    # --- Placeholder for Step 7: Leaderboard ---
    # (This might be shown regardless of login state, or after login)

# Allow direct execution for testing (streamlit run pages/student_app.py)
if __name__ == "__main__":
    # Mock necessary session state variables if running directly for testing
    # This is a simplified mock. In reality, parent_selector.py would set these.
    if 'datathon_train_file_name' not in st.session_state:
        st.session_state.datathon_train_file_name = "sample_train_data.csv" 
        st.info("Mocking datathon_train_file_name for direct run. Ensure secrets are configured.")
    
    show_student_page()
