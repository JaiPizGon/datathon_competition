import streamlit as st # For st.secrets, though direct use here is minimal
import json
import io
from modules import data_loader # To reuse get_drive_service if not passed directly
# from googleapiclient.errors import HttpError # Already in data_loader
# from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload # Already in data_loader

# --- UI Configuration Management ---
CONFIG_FILE_NAME = "datathon_hub_uiconfig.json"
DEFAULT_DRIVE_FOLDER_ID_FOR_CONFIG = None # Or specify a default folder ID like "root" or a specific one

DEFAULT_UI_SETTINGS = {
    "font_size": 14,            # Default font size in pixels
    "decimal_precision": 4,     # Default decimal places for scores
    "primary_color": "#FF4B4B", # Default primary theme color (Streamlit red)
    "secondary_color": "#FFFFFF", # Default secondary color (White)
    "background_color": "#0E1117", # Default Streamlit dark background
    "text_color": "#FAFAFA",       # Default Streamlit dark theme text
    # Add other UI settings as needed
}

def get_config_file_id(drive_service, folder_id=None, file_name=CONFIG_FILE_NAME):
    """Searches for the config file in Drive and returns its ID if found, else None."""
    if not drive_service:
        print("Error (config_manager.get_config_file_id): Drive service not available.")
        return None
    
    search_folder_id = folder_id if folder_id else DEFAULT_DRIVE_FOLDER_ID_FOR_CONFIG

    query_parts = [f"name='{file_name}'", "trashed=false"]
    if search_folder_id and search_folder_id.lower() != "root": # "root" is not an ID but a valid parent alias
        query_parts.append(f"'{search_folder_id}' in parents")
    elif not search_folder_id: # Search in root if no folder_id specified (or explicitly "root")
         # To search in root, you might need to specify 'root' as parent or omit parent clause based on API behavior
         # For simplicity, if no folder_id, it searches everywhere the user has access if parent clause omitted.
         # Let's assume for now it searches within the app's visible scope or root.
         pass


    query = " and ".join(query_parts)
    
    try:
        response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        if files:
            return files[0]['id'] # Return the ID of the first found file
        return None
    except Exception as e:
        print(f"Error (config_manager.get_config_file_id): Searching for config file '{file_name}': {e}")
        return None

def load_uiconfig_from_drive(drive_service, folder_id=None) -> dict:
    """
    Loads UI configuration from a JSON file on Google Drive.
    If the file is not found or an error occurs, returns default settings.
    """
    if not drive_service:
        print("Error (config_manager.load_uiconfig_from_drive): Drive service not available.")
        return DEFAULT_UI_SETTINGS.copy()

    config_file_id = get_config_file_id(drive_service, folder_id=folder_id, file_name=CONFIG_FILE_NAME)

    if config_file_id:
        try:
            # Use the download_csv_from_drive_to_dataframe logic, but for JSON
            # Re-implementing a focused part of it here for JSON
            request = drive_service.files().get_media(fileId=config_file_id)
            fh = io.BytesIO()
            # Need MediaIoBaseDownload from googleapiclient.http
            from googleapiclient.http import MediaIoBaseDownload
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            config_data = json.load(fh)
            # Merge with defaults to ensure all keys are present
            merged_config = DEFAULT_UI_SETTINGS.copy()
            merged_config.update(config_data)
            return merged_config
        except Exception as e:
            print(f"Error (config_manager.load_uiconfig_from_drive): Loading/parsing '{CONFIG_FILE_NAME}' (ID: {config_file_id}): {e}. Returning defaults.")
            return DEFAULT_UI_SETTINGS.copy()
    else:
        print(f"Info (config_manager.load_uiconfig_from_drive): Config file '{CONFIG_FILE_NAME}' not found. Returning defaults.")
        return DEFAULT_UI_SETTINGS.copy()

def save_uiconfig_to_drive(drive_service, config_dict: dict, folder_id=None) -> bool:
    """
    Saves UI configuration to a JSON file on Google Drive.
    Overwrites if file exists, creates new if not.
    """
    if not drive_service:
        print("Error (config_manager.save_uiconfig_to_drive): Drive service not available.")
        return False

    config_file_id = get_config_file_id(drive_service, folder_id=folder_id, file_name=CONFIG_FILE_NAME)
    
    file_content = json.dumps(config_dict, indent=4).encode('utf-8')
    fh = io.BytesIO(file_content)
    
    # Need MediaIoBaseUpload from googleapiclient.http
    from googleapiclient.http import MediaIoBaseUpload
    media_body = MediaIoBaseUpload(fh, mimetype='application/json', resumable=True)
    
    file_metadata = {'name': CONFIG_FILE_NAME}
    if folder_id and folder_id.lower() != "root": # Only add parents if folder_id is not root
        file_metadata['parents'] = [folder_id]
    # If no folder_id, it will be created in the user's "My Drive" root.

    try:
        if config_file_id: # File exists, update it
            updated_file = drive_service.files().update(
                fileId=config_file_id,
                media_body=media_body
                # body=file_metadata # Not typically needed for update if only content changes
            ).execute()
            # print(f"Info (config_manager.save_uiconfig_to_drive): Config file updated. ID: {updated_file.get('id')}")
        else: # File doesn't exist, create it
            created_file = drive_service.files().create(
                body=file_metadata,
                media_body=media_body,
                fields='id'
            ).execute()
            # print(f"Info (config_manager.save_uiconfig_to_drive): Config file created. ID: {created_file.get('id')}")
        return True
    except Exception as e:
        print(f"Error (config_manager.save_uiconfig_to_drive): Saving config file: {e}")
        return False

# Example of how data_loader.get_drive_service() might be used if not passed directly:
# def get_drive_service_from_data_loader():
#     # This assumes data_loader.py has get_drive_service() and handles its own auth state.
#     # This is just a conceptual link; direct passing of drive_service is cleaner.
#     drive_s = data_loader.get_drive_service() 
#     if not drive_s:
#         st.error("Failed to get Google Drive service via data_loader for config management.")
#         return None
#     return drive_s
