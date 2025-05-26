import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow # Corrected import, was Flow from google.auth.transport.requests
from google.auth.transport.requests import Request as GoogleAuthRequest # For token refresh
from googleapiclient.errors import HttpError 
import os 
import random
import string
from modules.config import MAX_TEAM_SIZE

SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_gspread_credentials():
    if 'gspread_credentials' in st.session_state:
        creds_dict = st.session_state.gspread_credentials
        # Ensure all necessary keys are present before attempting to create Credentials object
        if creds_dict.get('token') and creds_dict.get('client_id') and creds_dict.get('client_secret') and creds_dict.get('token_uri'):
            creds = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes') # Scopes should be part of the stored credentials
            )
            if creds and creds.valid:
                return creds
            elif creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(GoogleAuthRequest()) # Use google.auth.transport.requests.Request
                    # Update session state with the new token (and potentially new refresh token)
                    st.session_state.gspread_credentials = {
                        'token': creds.token, 'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri, 'client_id': creds.client_id,
                        'client_secret': creds.client_secret, 'scopes': creds.scopes
                    }
                    return creds
                except Exception as e:
                    st.error(f"Error refreshing Sheets token: {e}")
                    # Clear potentially corrupt/old credentials from session state
                    if 'gspread_credentials' in st.session_state: del st.session_state['gspread_credentials']
                    # Do not rerun here, let the flow continue to re-authenticate if needed
    
    # If no valid credentials in session state, start OAuth flow
    try:
        # Ensure st.secrets.google_oauth is accessed correctly
        if "google_oauth" not in st.secrets:
            st.error("Google OAuth configuration (google_oauth section) not found in st.secrets.")
            return None
            
        client_config_details = st.secrets["google_oauth"]
        client_config = {
            "web": {
                "client_id": client_config_details["client_id"],
                "project_id": client_config_details.get("project_id"), # Optional but good practice
                "auth_uri": client_config_details["auth_uri"],
                "token_uri": client_config_details["token_uri"],
                "auth_provider_x509_cert_url": client_config_details["auth_provider_x509_cert_url"],
                "client_secret": client_config_details["client_secret"],
                "redirect_uris": client_config_details["redirect_uris"] # This should be a list
            }
        }
        # The redirect URI used here must be one of the URIs registered in the Google Cloud Console
        redirect_uri = client_config["web"]["redirect_uris"][0]

        flow = Flow.from_client_config(client_config, scopes=SHEETS_SCOPES, redirect_uri=redirect_uri)
    except KeyError as e:
        st.error(f"Required key missing in Google OAuth configuration (st.secrets.google_oauth): {e}. Ensure client_id, client_secret, auth_uri, token_uri, auth_provider_x509_cert_url, redirect_uris are present.")
        return None
    except Exception as e: # Catch other potential errors during flow setup
        st.error(f"Error loading Google OAuth configuration for Sheets: {e}")
        return None

    # Check for authorization code in query parameters
    query_params = st.experimental_get_query_params()
    auth_code_tuple = query_params.get("code")

    if auth_code_tuple:
        auth_code = auth_code_tuple[0] # query_params returns a list
        try:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            # Store credentials in session state as a serializable dict
            st.session_state.gspread_credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token, # Might be None if not requested or not granted
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            # Clear the auth code from query params by redirecting to base URL (or current page without params)
            st.experimental_set_query_params() 
            st.rerun() # Rerun to use the new credentials and clear the auth UI
        except Exception as e:
            st.error(f"Error fetching Sheets token: {e}")
            return None
    else:
        # No auth code, so generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # Request a refresh token
            prompt='consent'        # Ensure user consents (useful for dev)
        )
        st.markdown(f"""
        Please [authenticate with Google for Sheets access]({authorization_url}) 
        to allow this application to interact with your Google Sheets.
        After authentication, you will be redirected back to the app.
        """)
        return None # Important to return None to signal that auth is pending

    return None # Default return if no path leads to credentials

def get_gspread_client():
    credentials = get_gspread_credentials()
    if credentials:
        try:
            client = gspread.authorize(credentials)
            # st.success("Successfully authorized gspread client.") # Optional success message
            return client
        except Exception as e:
            st.error(f"Failed to authorize gspread client: {e}")
            # Clearing credentials might be too aggressive if it's a temporary gspread issue,
            # but can help if the token is truly problematic.
            if 'gspread_credentials' in st.session_state:
                del st.session_state['gspread_credentials']
            st.warning("Cleared Sheets credentials due to authorization error. Please try re-authenticating.")
            st.rerun() # Rerun to trigger the auth flow again
            return None
    # If credentials are None (auth pending or failed), this will also return None
    return None

def connect_to_workbook(gspread_client, workbook_name: str):
    if not gspread_client:
        st.error("gspread client not available. Cannot connect to workbook.")
        return None
    if not workbook_name:
        st.error("Workbook name not provided.")
        return None
        
    try:
        spreadsheet = gspread_client.open(workbook_name)
        st.success(f"Successfully connected to workbook: '{workbook_name}'")
        return spreadsheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet '{workbook_name}' not found. Ensure the name is correct and the authenticated user has access.")
        return None
    except Exception as e: # Catch other gspread or general exceptions
        st.error(f"An error occurred while opening workbook '{workbook_name}': {e}")
        return None

def get_max_team_size() -> int:
    """Returns the configured maximum team size."""
    return MAX_TEAM_SIZE

def get_or_create_datathon_teams_worksheet(spreadsheet: gspread.Spreadsheet, datathon_id: str) -> gspread.worksheet.Worksheet | None:
    """
    Gets or creates a worksheet within the given spreadsheet for a specific datathon.
    This worksheet will serve as the 'Teams' sheet for that datathon.
    Ensures the worksheet has the correct header row for team management.

    Args:
        spreadsheet: The authenticated gspread.Spreadsheet object (e.g., "DatathonTeams").
        datathon_id: A unique identifier for the datathon (e.g., "Datathon_July2024_Regression").

    Returns:
        A gspread.Worksheet object if successful, None otherwise.
    """
    if not spreadsheet:
        st.error("Spreadsheet object not provided. Cannot get or create datathon worksheet.")
        return None
    if not datathon_id or not datathon_id.strip():
        st.error("Datathon ID is invalid. Cannot create worksheet.")
        return None

    try:
        # Try to get the worksheet by its title (datathon_id)
        worksheet = spreadsheet.worksheet(datathon_id)
        # st.info(f"Found existing worksheet for datathon: '{datathon_id}'.")
    except gspread.exceptions.WorksheetNotFound:
        try:
            # st.info(f"Worksheet for datathon '{datathon_id}' not found. Creating new one...")
            worksheet = spreadsheet.add_worksheet(title=datathon_id, rows=100, cols=20) # Adjust rows/cols as needed
            # st.success(f"Successfully created worksheet: '{datathon_id}'.")
        except Exception as e: # Broad exception for creation failure
            st.error(f"Failed to create new worksheet '{datathon_id}': {e}")
            return None
    except Exception as e: # Broad exception for other gspread errors
         st.error(f"An unexpected error occurred while trying to access worksheet '{datathon_id}': {e}")
         return None

    # Define header row based on MAX_TEAM_SIZE
    max_members = get_max_team_size()
    header = ["TeamName", "Password"] + [f"Member{i+1}" for i in range(max_members)]

    try:
        # Check if the first row matches the header.
        # gspread.utils.rowcol_to_a1(1, col_num) can convert col number to A1 notation
        # worksheet.row_values(1) fetches the first row
        current_header = worksheet.row_values(1) # Might raise error if sheet is completely empty
        
        if current_header != header:
            # st.info(f"Header mismatch or missing in worksheet '{datathon_id}'. Current: {current_header}. Expected: {header}. Updating header...")
            # Update header. This overwrites the first row.
            # Ensure worksheet is large enough for header if it was pre-existing and small
            if worksheet.col_count < len(header):
                worksheet.add_cols(len(header) - worksheet.col_count)

            worksheet.update('A1', [header]) # Update the first row with the new header
            # st.success(f"Header updated for worksheet '{datathon_id}'.")
        # else:
            # st.info(f"Header is already correct in worksheet '{datathon_id}'.")

    except gspread.exceptions.APIError as api_error:
        # This can happen if the sheet is completely empty and worksheet.row_values(1) is called.
        # Or if there are permission issues not caught by initial connection.
        # st.warning(f"APIError checking/updating header for '{datathon_id}': {api_error}. Attempting to set header directly.")
        try:
            if worksheet.col_count < len(header):
                worksheet.add_cols(len(header) - worksheet.col_count)
            worksheet.update('A1', [header])
            # st.success(f"Header set for (previously empty or problematic) worksheet '{datathon_id}'.")
        except Exception as e:
            st.error(f"Failed to set header for worksheet '{datathon_id}' even after APIError: {e}")
            return None # Cannot guarantee sheet is usable
    except Exception as e:
        st.error(f"An unexpected error occurred while checking/updating header for '{datathon_id}': {e}")
        return None


    return worksheet

def generate_random_password(length=8):
    """Generates a random alphanumeric password."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def create_new_team(teams_worksheet: gspread.worksheet.Worksheet, team_name: str, student_id: str) -> tuple[str, str] | None:
    """
    Creates a new team in the given 'Teams' worksheet.

    Args:
        teams_worksheet: The gspread.Worksheet object for team management.
        team_name: The desired name for the new team.
        student_id: The ID or email of the first student joining the team.

    Returns:
        A tuple (team_name, generated_password) if successful.
        None if the team name already exists or an error occurs.
    """
    if not teams_worksheet:
        st.error("Teams worksheet not provided. Cannot create team.")
        return None
    if not team_name.strip() or not student_id.strip():
        st.error("Team name or student ID is invalid.")
        return None

    try:
        # Check if team name already exists (case-insensitive check for robustness)
        # Fetch all team names from the first column.
        # This assumes TeamName is always in the first column (A).
        # Skip header row by slicing from the second element: all_records()[1:] or get_all_values()[1:]
        existing_team_names = teams_worksheet.col_values(1)[1:] # Get all values from 1st col, skip header
        if team_name.lower() in [name.lower() for name in existing_team_names]:
            st.warning(f"Team name '{team_name}' already exists. Please choose a different name.")
            return None

        password = generate_random_password()
        
        # Prepare the new row. Member1 is student_id, others are initially empty.
        max_members = get_max_team_size() # From modules.config via local function
        new_row = [team_name, password, student_id] + [""] * (max_members - 1)
        
        teams_worksheet.append_row(new_row, value_input_option='USER_ENTERED')
        # st.success(f"Team '{team_name}' created successfully with password '{password}'.")
        return team_name, password

    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error while creating team '{team_name}': {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while creating team '{team_name}': {e}")
        return None

def join_team(teams_worksheet: gspread.worksheet.Worksheet, team_name: str, password: str, student_id: str) -> bool:
    """
    Allows a student to join an existing team in the 'Teams' worksheet.

    Args:
        teams_worksheet: The gspread.Worksheet object for team management.
        team_name: The name of the team to join.
        password: The password for the team.
        student_id: The ID or email of the student wishing to join.

    Returns:
        True if the student successfully joined the team.
        False otherwise (e.g., team not found, wrong password, team full, student already in team).
    """
    if not teams_worksheet:
        st.error("Teams worksheet not provided. Cannot join team.")
        return False
    if not all([team_name.strip(), password, student_id.strip()]): # Password can be anything, so no .strip()
        st.error("Team name, password, or student ID is invalid.")
        return False

    try:
        # Find the team row by team_name (case-insensitive for robustness)
        # This assumes TeamName is always in the first column (A).
        all_team_names_with_case = teams_worksheet.col_values(1) # Includes header
        
        # Find index, being mindful of header row and case
        found_row_index = -1
        for i, name_in_sheet in enumerate(all_team_names_with_case):
            if name_in_sheet.lower() == team_name.lower():
                if i == 0: # Header row
                    st.error("Error: Team name matches header row. This should not happen.")
                    return False 
                found_row_index = i + 1 # gspread rows are 1-indexed
                break
        
        if found_row_index == -1:
            st.warning(f"Team '{team_name}' not found.")
            return False

        # Retrieve the entire row for the found team
        team_row_values = teams_worksheet.row_values(found_row_index)

        # Verify password (assuming Password is in the second column B)
        stored_password = team_row_values[1] if len(team_row_values) > 1 else None
        if stored_password != password:
            st.warning(f"Incorrect password for team '{team_name}'.")
            return False

        # Check if student is already in the team (Member columns start from index 2)
        member_columns = team_row_values[2:]
        if student_id in member_columns:
            st.info(f"Student '{student_id}' is already a member of team '{team_name}'.")
            # Depending on desired behavior, this could be True or a specific message.
            # For "joining", if already a member, it's not a new join action.
            return False # Or True if "being in the team" counts as "joined"

        # Find the next empty "MemberX" column
        # Member columns start at index 2 in team_row_values list (Column C in sheets)
        max_members = get_max_team_size()
        first_empty_member_col_index_in_row = -1 # Index within team_row_values
        
        # Iterate from Member1 up to MaxMembers
        # Column C is index 2, D is 3, etc. Member1 is at team_row_values[2]
        for i in range(max_members):
            member_col_in_row_values = 2 + i # Index in team_row_values list
            if member_col_in_row_values < len(team_row_values) and not team_row_values[member_col_in_row_values].strip():
                first_empty_member_col_index_in_row = member_col_in_row_values
                break
            elif member_col_in_row_values >= len(team_row_values): # Cell doesn't exist, means it's empty
                first_empty_member_col_index_in_row = member_col_in_row_values
                break 
        
        if first_empty_member_col_index_in_row == -1:
            st.warning(f"Team '{team_name}' is already full (max {max_members} members).")
            return False

        # Update the sheet: Add student_id to the found empty member column
        # Convert list index to sheet column (1-indexed: A=1, B=2, ...)
        # first_empty_member_col_index_in_row is 0-indexed for the list, 
        # but refers to content starting from column C.
        # So, if it's 2, it's the 3rd item, hence column C.
        sheet_col_to_update = first_empty_member_col_index_in_row + 1 
        
        teams_worksheet.update_cell(found_row_index, sheet_col_to_update, student_id)
        # st.success(f"Student '{student_id}' successfully joined team '{team_name}'.")
        return True

    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error while joining team '{team_name}': {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred while joining team '{team_name}': {e}")
        return False

def remove_team_member(teams_worksheet: gspread.worksheet.Worksheet, team_name: str, member_student_id_to_remove: str) -> bool:
    """
    Removes a specific member from a team in the 'Teams' worksheet. (Admin action)

    Args:
        teams_worksheet: The gspread.Worksheet object for team management.
        team_name: The name of the team to modify.
        member_student_id_to_remove: The ID or email of the student to remove.

    Returns:
        True if the member was successfully removed.
        False otherwise (e.g., team not found, member not found in team).
    """
    if not teams_worksheet:
        st.error("Teams worksheet not provided. Cannot remove member.")
        return False
    if not all([team_name.strip(), member_student_id_to_remove.strip()]):
        st.error("Team name or member ID for removal is invalid.")
        return False

    try:
        # Find the team row by team_name (case-insensitive)
        all_team_names_with_case = teams_worksheet.col_values(1) # Includes header
        found_row_index = -1
        for i, name_in_sheet in enumerate(all_team_names_with_case):
            if name_in_sheet.lower() == team_name.lower():
                if i == 0: # Header row
                    st.error("Error: Team name matches header row. Cannot modify.")
                    return False
                found_row_index = i + 1 # gspread rows are 1-indexed
                break
        
        if found_row_index == -1:
            st.warning(f"Team '{team_name}' not found. Cannot remove member.")
            return False

        team_row_values = teams_worksheet.row_values(found_row_index)
        
        # Find the member in MemberX columns (starting from index 2 of team_row_values)
        member_col_to_clear = -1 # 1-indexed sheet column
        for i in range(2, len(team_row_values)): # Iterate through Member columns
            if team_row_values[i] == member_student_id_to_remove:
                member_col_to_clear = i + 1 # Convert 0-indexed list to 1-indexed sheet col
                break
        
        if member_col_to_clear == -1:
            st.warning(f"Member '{member_student_id_to_remove}' not found in team '{team_name}'.")
            return False

        # Clear the cell
        teams_worksheet.update_cell(found_row_index, member_col_to_clear, "")
        # st.success(f"Member '{member_student_id_to_remove}' removed from team '{team_name}'.")
        return True

    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error while removing member from '{team_name}': {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred while removing member from '{team_name}': {e}")
        return False

def reset_team_password(teams_worksheet: gspread.worksheet.Worksheet, team_name: str) -> str | None:
    """
    Resets the password for a given team. (Admin action)

    Args:
        teams_worksheet: The gspread.Worksheet object for team management.
        team_name: The name of the team whose password needs resetting.

    Returns:
        The new password if successful, None otherwise.
    """
    if not teams_worksheet:
        st.error("Teams worksheet not provided. Cannot reset password.")
        return None
    if not team_name.strip():
        st.error("Team name is invalid.")
        return None

    try:
        # Find the team row by team_name (case-insensitive)
        all_team_names_with_case = teams_worksheet.col_values(1) # Includes header
        found_row_index = -1
        for i, name_in_sheet in enumerate(all_team_names_with_case):
            if name_in_sheet.lower() == team_name.lower():
                if i == 0: # Header row
                    st.error("Error: Team name matches header row. Cannot modify.")
                    return False # Should be None as per return type, but False indicates failure too
                found_row_index = i + 1 # gspread rows are 1-indexed
                break

        if found_row_index == -1:
            st.warning(f"Team '{team_name}' not found. Cannot reset password.")
            return None

        new_password = generate_random_password()
        
        # Update the password cell (assuming Password is in the second column B, which is col index 2)
        teams_worksheet.update_cell(found_row_index, 2, new_password)
        # st.success(f"Password for team '{team_name}' has been reset to: {new_password}")
        return new_password

    except gspread.exceptions.APIError as e:
        st.error(f"Google Sheets API error while resetting password for '{team_name}': {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while resetting password for '{team_name}': {e}")
        return None

# Placeholder for other functions
# Example:
# def get_worksheet_data(workbook, worksheet_name: str):
#     try:
#         worksheet = workbook.worksheet(worksheet_name)
#         return worksheet.get_all_records() # Or get_all_values()
#     except gspread.exceptions.WorksheetNotFound:
#         st.error(f"Worksheet '{worksheet_name}' not found in the workbook.")
#         return None
#     except Exception as e:
#         st.error(f"Error accessing worksheet '{worksheet_name}': {e}")
#         return None
