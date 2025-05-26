import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import io # For BytesIO or StringIO if needed for wrapping file content
import os # For future use if handling client_secret.json directly, though st.secrets is preferred

# Define the scopes needed for the application
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']
# Placeholder for the path to client_secret.json if loaded from file system
# However, we will primarily rely on st.secrets
# CLIENT_SECRETS_FILE = 'secrets/client_secret.json' 

def get_google_credentials():
    # Try to load credentials from session_state first
    if 'google_credentials' in st.session_state:
        # Ensure that st.session_state.google_credentials is a dict that can be passed to Credentials
        creds_info = st.session_state.google_credentials
        # Check if creds_info is already a Credentials object (less likely if stored from dict)
        if isinstance(creds_info, Credentials):
            if creds_info.valid:
                 return creds_info
        elif isinstance(creds_info, dict): # Expected case
            try:
                creds = Credentials(**creds_info)
                if creds and creds.valid:
                    return creds
                # If expired and refresh token exists, it should auto-refresh if used by a service call.
                # If not, or no refresh token, proceed to re-authenticate.
                # google-auth library handles refresh automatically if refresh_token is present.
                if creds and creds.expired and creds.refresh_token:
                    # The library will attempt to refresh it when a request is made.
                    # No explicit st.rerun() needed here unless a service call fails and needs user action.
                    return creds 
            except Exception as e:
                st.warning(f"Error loading credentials from session state: {e}. Re-authenticating.")
                del st.session_state.google_credentials # Clear potentially corrupt state


    # If not in session_state or not valid, try to authenticate
    try:
        # Construct client_config from st.secrets
        # Streamlit expects secrets in secrets.toml.
        # Example secrets.toml structure:
        # [google_oauth]
        # client_id = "YOUR_CLIENT_ID"
        # client_secret = "YOUR_CLIENT_SECRET"
        # redirect_uris = ["http://localhost:8501"] # Or your deployed app's URL
        # auth_uri = "https://accounts.google.com/o/oauth2/auth"
        # token_uri = "https://oauth2.googleapis.com/token"
        # auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        # project_id = "YOUR_PROJECT_ID" # Optional

        client_config_dict = {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "project_id": st.secrets["google_oauth"].get("project_id"), # Optional but good practice
                "auth_uri": st.secrets["google_oauth"]["auth_uri"],
                "token_uri": st.secrets["google_oauth"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["google_oauth"]["auth_provider_x509_cert_url"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "redirect_uris": st.secrets["google_oauth"]["redirect_uris"] # This should be a list
            }
        }
        # The redirect URI used here must be one of the URIs registered in the Google Cloud Console
        # For local development, http://localhost:8501 is common for Streamlit.
        redirect_uri = client_config_dict["web"]["redirect_uris"][0]

        flow = Flow.from_client_config(
            client_config_dict,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    except KeyError as e:
        st.error(f"Google OAuth configuration key missing in st.secrets: {e}. Please ensure 'google_oauth' section with all required fields (client_id, client_secret, auth_uri, token_uri, auth_provider_x509_cert_url, redirect_uris) is in your secrets.toml.")
        return None
    except Exception as e:
        st.error(f"Error loading Google OAuth configuration from st.secrets: {e}")
        return None

    # Check for authorization code in query parameters (after redirect from Google)
    query_params = st.experimental_get_query_params()
    auth_code_list = query_params.get("code")

    if auth_code_list:
        auth_code = auth_code_list[0] # query_params returns a list
        try:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            # Store credentials in session state as a serializable dict
            st.session_state.google_credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            # Clear the auth code from query params by redirecting to base URL (or current page without params)
            st.experimental_set_query_params() 
            # st.rerun() # Rerun to update UI and use credentials
            # Instead of immediate rerun, let the calling function (get_drive_service) get the creds and proceed.
            # A rerun might be needed if the UI needs to change significantly post-auth.
            return Credentials(**st.session_state.google_credentials)
        except Exception as e:
            st.error(f"Error fetching OAuth token: {e}")
            return None
    else:
        # No auth code, so generate authorization URL and ask user to authenticate
        authorization_url, _ = flow.authorization_url(
            access_type='offline',  # Request a refresh token
            prompt='consent'        # Ensure user consents (useful for dev, can be 'select_account' for prod)
        )
        st.markdown(f"""
        Please authenticate with Google Drive to allow this application to access your files.
        <a href="{authorization_url}" target="_blank">Click here to Authenticate</a>
        """, unsafe_allow_html=True)
        st.info("After successful authentication, you will be redirected back to the app. The page might reload.")
        # An st.text_input for code is a fallback if redirect method fails or for certain OAuth flows.
        # For Streamlit, query_params is the primary way.
        # manual_auth_code = st.text_input("If redirected to a page with a code, or if auto-redirect fails, please paste the code here:")
        # if manual_auth_code:
        #    # This part would be similar to the auth_code_list block above
        #    # but is generally not needed if redirect_uri is correctly configured.
        #    st.warning("Manual code entry is a fallback and may not work with all configurations.")
        return None

    return None # Should not be reached if logic is correct

def get_drive_service():
    """Builds and returns a Google Drive API service object if authenticated."""
    credentials = get_google_credentials()
    if credentials:
        if not credentials.valid: # Check if credentials are valid (e.g. token not expired)
            if credentials.expired and credentials.refresh_token:
                try:
                    # Attempt to refresh the credentials
                    # The google-auth library typically handles this automatically on the first API call
                    # Forcing a refresh can be done but often isn't necessary unless you want to handle the error explicitly
                    # For now, let's assume the library handles it or the next API call will fail and trigger re-auth
                    st.info("Google credentials expired, attempting to refresh...")
                    # credentials.refresh(Request()) # Requires google.auth.transport.requests.Request
                    # For now, rely on automatic refresh or re-authentication flow
                except Exception as e:
                    st.error(f"Error refreshing token: {e}")
                    if 'google_credentials' in st.session_state:
                        del st.session_state['google_credentials']
                    st.rerun() # Force re-authentication
                    return None
            else: # Invalid and no refresh token
                st.warning("Google credentials are invalid and no refresh token is available. Please re-authenticate.")
                if 'google_credentials' in st.session_state:
                    del st.session_state['google_credentials']
                # Trigger re-authentication by calling get_google_credentials again implicitly on next run or manually
                # st.rerun() # This might cause a loop if not handled carefully.
                # Let the get_google_credentials() handle showing auth link again.
                return None # No valid credentials

        # If credentials are valid or refreshable by library
        try:
            service = build('drive', 'v3', credentials=credentials)
            # Test call to check if token is valid and refresh works
            # service.about().get(fields="user").execute() 
            # st.success("Successfully connected to Google Drive.") # Optional success message
            return service
        except HttpError as error:
            st.error(f"An API error occurred with Google Drive: {error.reason}")
            if error.resp.status in [401, 403]: # Unauthorized or Forbidden
                # Token might be revoked or scopes insufficient
                if 'google_credentials' in st.session_state:
                    del st.session_state['google_credentials']
                st.warning("Authentication failed, token might be invalid/revoked, or scopes insufficient. Please re-authenticate.")
                # st.rerun() # This will trigger the auth flow again
            return None
        except Exception as e:
            st.error(f"Failed to build Google Drive service: {e}")
            return None
    else:
        # Message already handled by get_google_credentials (auth link or error)
        # st.info("Google Drive authentication is required to proceed.")
        pass # Let get_google_credentials handle the UI for auth
    return None

# Placeholder for other functions to be added later
def display_file_uploaders(competition_type: str) -> dict:
    # Your implementation here
    uploaded_files_dict = {}
    
    uploaded_files_dict['train'] = st.file_uploader(
        "Upload Training Data (CSV)", 
        type=['csv'],
        help="Upload the CSV file containing the training dataset."
    )
    
    sensitive_competition_types = ['ARIMA', 'ARMA', 'SARIMA']
    if competition_type.upper() not in sensitive_competition_types:
        uploaded_files_dict['test_inputs'] = st.file_uploader(
            "Upload Test Inputs Data (CSV)", 
            type=['csv'],
            help="Upload the CSV file containing the input features for the test dataset."
        )
        uploaded_files_dict['test_outputs'] = st.file_uploader(
            "Upload Test Outputs Data (CSV)", 
            type=['csv'],
            help="Upload the CSV file containing the target variable for the test dataset."
        )
    else:
        # Ensure keys exist even if not used, or handle missing keys in consuming code
        uploaded_files_dict['test_inputs'] = None
        uploaded_files_dict['test_outputs'] = None
        
    return uploaded_files_dict

# Consider making this configurable via st.secrets
DEFAULT_TARGET_DRIVE_FOLDER_ID = "REPLACE_WITH_YOUR_ACTUAL_GOOGLE_DRIVE_FOLDER_ID"

def upload_csvs_to_drive(uploaded_files: dict, unique_id: str, drive_service) -> dict:
    # Your implementation here
    file_ids_map = {}

    try:
        target_folder_id = st.secrets["google_drive"]["target_folder_id"]
    except (KeyError, AttributeError): # AttributeError if st.secrets.google_drive is not a dict-like object
        st.warning(f"Target Google Drive folder ID not found in st.secrets.google_drive.target_folder_id. "
                   f"Using default placeholder: {DEFAULT_TARGET_DRIVE_FOLDER_ID}. "
                   f"Please configure this in your secrets.toml for proper operation.")
        target_folder_id = DEFAULT_TARGET_DRIVE_FOLDER_ID
    
    if not drive_service:
        st.error("Google Drive service not available. Cannot upload files.")
        # Ensure all expected keys are in the map, even if None
        for key_to_check in ['train', 'test_inputs', 'test_outputs']:
             if key_to_check in uploaded_files: # only add if it was an expected key
                file_ids_map[key_to_check] = None
        return file_ids_map

    for key, uploaded_file_obj in uploaded_files.items():
        if uploaded_file_obj is not None:
            if key == 'train':
                drive_filename = f"train_{unique_id}.csv"
            elif key == 'test_inputs':
                drive_filename = f"test_inputs_{unique_id}.csv"
            elif key == 'test_outputs':
                drive_filename = f"test_outputs_{unique_id}.csv"
            else:
                st.warning(f"Unknown file type key '{key}'. Skipping upload.")
                file_ids_map[key] = None # Mark as not uploaded
                continue

            file_metadata = {
                'name': drive_filename,
                'parents': [target_folder_id]
            }
            
            try:
                # Reset read pointer of the BytesIO object from Streamlit
                uploaded_file_obj.seek(0)
                
                media = MediaIoBaseUpload(
                    uploaded_file_obj,
                    mimetype='text/csv',
                    resumable=True
                )
                
                request = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                )
                
                # For simplicity, direct execution is shown here.
                # For large files, consider implementing resumable upload with progress:
                # response = None
                # with st.spinner(f"Uploading {drive_filename}..."):
                #     while response is None:
                #         status, response = request.next_chunk()
                #         if status:
                #             st.progress(status.progress()) # Show progress bar
                # file = response
                
                file = request.execute()
                
                file_id = file.get('id')
                file_ids_map[key] = file_id
                st.success(f"Successfully uploaded '{drive_filename}' to Google Drive. File ID: {file_id}")

            except HttpError as error:
                error_details = "No additional details."
                try:
                    # Attempt to parse error content if it's JSON (common for Google API errors)
                    if error.content:
                        error_content_decoded = error.content.decode('utf-8')
                        error_details = f"Details: {error_content_decoded}"
                except Exception: # Fallback if decoding/parsing fails
                     error_details = f"Raw error content: {error.content}"

                st.error(f"An API error occurred while uploading '{drive_filename}': {error}. {error_details}")
                file_ids_map[key] = None
            except Exception as e:
                st.error(f"An unexpected error occurred while uploading '{drive_filename}': {e}")
                file_ids_map[key] = None
        else:
            # Ensure key exists in map even if file object was None (e.g. for ARIMA models)
            file_ids_map[key] = None 

    # Ensure all expected keys ('train', 'test_inputs', 'test_outputs') are in file_ids_map
    # This handles cases where a key might have been skipped (e.g., unknown key) or if it wasn't in uploaded_files initially
    for expected_key in ['train', 'test_inputs', 'test_outputs']:
        if expected_key not in file_ids_map:
            file_ids_map[expected_key] = None
            
    return file_ids_map

def get_drive_shareable_link(file_id: str, drive_service) -> str | None:
    if not drive_service:
        st.error("Google Drive service not available. Cannot get shareable link.")
        return None
    if not file_id:
        st.warning("No file ID provided to get shareable link.")
        return None

    try:
        # First, try to set/ensure 'anyone with link can read' permission
        permission_body = {'type': 'anyone', 'role': 'reader'}
        drive_service.permissions().create(
            fileId=file_id,
            body=permission_body,
            # Not sending email notification
            # sendNotificationEmail=False 
        ).execute()
        
        # After ensuring permission, get the file metadata including the webViewLink
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id, name, webViewLink' # webViewLink should now be accessible
        ).execute()
        
        shareable_link = file_metadata.get('webViewLink')
        
        if shareable_link:
            # st.success(f"Successfully obtained shareable link for file: {file_metadata.get('name')}")
            return shareable_link
        else:
            st.error(f"Could not retrieve shareable link for file ID {file_id} even after setting permissions.")
            return None

    except HttpError as error:
        # A common error is 403 if 'anyone' permission already exists or conflicts.
        # In such cases, the webViewLink might still be obtainable if the existing permission is sufficient.
        if error.resp.status == 403:
             st.warning(f"Could not create/update permission for file ID {file_id} (it might already exist or be restricted by domain policy): {error.content.decode()}. Attempting to retrieve existing link.")
             # Try to get the link anyway
             try:
                file_metadata = drive_service.files().get(fileId=file_id, fields='webViewLink, name').execute()
                link = file_metadata.get('webViewLink')
                if link:
                    # st.info(f"Retrieved existing shareable link for {file_metadata.get('name')}.")
                    return link
                else:
                    st.error(f"No shareable link found for {file_id} after permission issue.")
                    return None
             except HttpError as e:
                st.error(f"API error retrieving link for {file_id} after initial permission error: {e.content.decode()}")
                return None
        else:
            st.error(f"API error processing file ID {file_id}: {error.content.decode()}")
            return None
    except Exception as e:
        st.error(f"An unexpected error occurred with file ID {file_id}: {e}")
        return None

def list_csv_files_from_drive(drive_service, folder_id: str = None) -> list:
    if not drive_service:
        st.error("Google Drive service not available. Cannot list files.")
        return []

    actual_folder_id = folder_id
    if not actual_folder_id:
        try:
            actual_folder_id = st.secrets["google_drive"]["target_folder_id"]
        except (KeyError, AttributeError):
            st.warning(f"Target Google Drive folder ID not found in st.secrets.google_drive.target_folder_id. "
                       f"Using default placeholder: {DEFAULT_TARGET_DRIVE_FOLDER_ID} to list files. "
                       f"Please configure this in your secrets.toml.")
            actual_folder_id = DEFAULT_TARGET_DRIVE_FOLDER_ID
            if actual_folder_id == "REPLACE_WITH_YOUR_ACTUAL_GOOGLE_DRIVE_FOLDER_ID":
                 st.error("Default folder ID is still the placeholder. Cannot list files without a valid folder ID.")
                 return[]


    csv_files = []
    try:
        query = f"'{actual_folder_id}' in parents and mimeType='text/csv' and trashed=false"
        
        page_token = None
        while True:
            response = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageSize=100, # Max 1000, but 100 is common for page size
                pageToken=page_token
            ).execute()
            
            for file_item in response.get('files', []):
                csv_files.append({'id': file_item.get('id'), 'name': file_item.get('name')})
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        
        if csv_files:
            # Sort by name for consistent display
            csv_files = sorted(csv_files, key=lambda x: x['name'].lower())
            # st.info(f"Found {len(csv_files)} CSV files in the target folder.")
        # else:
            # st.info("No CSV files found in the target Google Drive folder.")
            
    except HttpError as error:
        st.error(f"An API error occurred while listing CSV files: {error.content.decode()}")
        return [] # Return empty list on error
    except Exception as e:
        st.error(f"An unexpected error occurred while listing CSV files: {e}")
        return []
        
    return csv_files
