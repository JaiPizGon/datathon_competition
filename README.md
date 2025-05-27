# Datathon Hub

This project is a Streamlit application for managing datathon activities.

## Setup

1.  **Create a Python virtual environment:**
    ```bash
    python -m venv .venv
    ```

2.  **Activate the virtual environment:**
    - On Windows:
      ```bash
      .venv\Scripts\activate
      ```
    - On macOS and Linux:
      ```bash
      source .venv/bin/activate
      ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Streamlit app:**
    ```bash
    streamlit run app.py
    ```

## Google Drive Integration Setup

To use the Google Drive upload features, you need to set up a Google Cloud Project, enable the Google Drive API, and create OAuth 2.0 credentials.

### 1. Set up a Google Cloud Project

*   Go to the [Google Cloud Console](https://console.cloud.google.com/).
*   Create a new project or select an existing one.

### 2. Enable Google APIs
*   In your Google Cloud Project, navigate to "APIs & Services" > "Library".
*   Search for "Google Drive API" and enable it.
*   Search for "Google Sheets API" and enable it as well.

### 3. Create OAuth 2.0 Credentials

*   Navigate to "APIs & Services" > "Credentials".
*   Click "+ CREATE CREDENTIALS" and select "OAuth client ID".
*   If prompted, configure the "OAuth consent screen":
    *   **User Type:** Choose "External" (unless you are a Google Workspace user and want to restrict to your organization).
    *   **App name:** Enter an application name (e.g., "Datathon Hub Uploader").
    *   **User support email:** Your email address.
    *   **App domain (optional):** You can leave these blank for now.
    *   **Developer contact information:** Your email address.
    *   Click "SAVE AND CONTINUE".
    *   **Scopes:** You can skip adding scopes here as the application specifies them. Click "SAVE AND CONTINUE".
    *   **Test users:** Add your Google account(s) that will be testing the application. Click "SAVE AND CONTINUE".
    *   Review the summary and go back to the dashboard.
*   Now, create the OAuth client ID again:
    *   **Application type:** Select "Web application".
    *   **Name:** Give your client ID a name (e.g., "Datathon Hub Web Client").
    *   **Authorized JavaScript origins:** Not strictly needed for this backend flow, but you can add your Streamlit app's base URL if you plan to use client-side Google Sign-In later (e.g., `http://localhost:8501`).
    *   **Authorized redirect URIs:** This is crucial. Add the URI where your Streamlit app will be running and receive the OAuth code.
        *   For local development: `http://localhost:8501`
        *   For deployed apps, use the deployed app's URL (e.g., `https://your-streamlit-app.com`)
        *   *Ensure this matches what's used in `modules/data_loader.py`.*
    *   Click "CREATE".
*   A dialog will show your "Client ID" and "Client Secret". **Download the JSON file** by clicking "DOWNLOAD JSON". Rename this file to `client_secret.json` and keep it secure. **Do NOT commit this file to Git directly.**

### 4. Configure Streamlit Secrets

Streamlit uses a `secrets.toml` file to store sensitive information. Create a file named `.streamlit/secrets.toml` in the root of your project directory (you might need to create the `.streamlit` folder first).

Add the content of your downloaded `client_secret.json` and other necessary configurations to `.streamlit/secrets.toml` like this:

```toml
# .streamlit/secrets.toml

[google_oauth]
# These values are taken directly from the "web" key in your downloaded client_secret.json
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
project_id = "YOUR_PROJECT_ID" # Can be found in your Google Cloud Console
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_secret = "YOUR_CLIENT_SECRET"
# Ensure this list includes the redirect URI used by the app (e.g., http://localhost:8501 for local)
redirect_uris = ["http://localhost:8501", "YOUR_DEPLOYED_APP_URL_HERE_IF_APPLICABLE"] 

# Optional: If you obtain a user's refresh token and want to store it for prolonged access
# (requires careful security consideration and user consent management)
# [google_user_token]
# token = "USER_ACCESS_TOKEN"
# refresh_token = "USER_REFRESH_TOKEN"
# token_uri = "https://oauth2.googleapis.com/token" # Usually same as above
# client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
# client_secret = "YOUR_CLIENT_SECRET"
# scopes = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive.metadata.readonly"]

[google_drive]
# Replace with the ID of the Google Drive folder where files should be uploaded.
# To get a folder ID, open the folder in Google Drive. The ID is the last part of the URL.
# e.g., if URL is https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ,
# the ID is 1aBcDeFgHiJkLmNoPqRsTuVwXyZ
target_folder_id = "YOUR_GOOGLE_DRIVE_TARGET_FOLDER_ID_FOR_DATASETS"

[google_sheets]
# Name of the Google Sheets workbook for team management.
# Ensure this sheet is shared with the Google account used for OAuth.
datathon_teams_workbook_name = "DatathonTeams" 
```

### 5. Share the "DatathonTeams" Google Sheet (Important!)

For the application to access and manage the "DatathonTeams" Google Sheet:

*   Create a new Google Sheet named **"DatathonTeams"** in your Google Drive (or use the name you configured in `secrets.toml` under `google_sheets.datathon_teams_workbook_name`).
*   The Google account associated with the OAuth credentials you configured (the one you use to log in when the app asks for Google authentication) **must have edit permissions** for this "DatathonTeams" sheet.
*   Alternatively, if you were using a Service Account (not covered in current setup), you would share the sheet with the service account's email address. With the current OAuth (user-based) setup, your own user account needs access.

**Important Security Notes:**
*   The `.streamlit/secrets.toml` file should **NOT** be committed to your Git repository if it contains real secrets. Ensure your project's `.gitignore` file includes `.streamlit/secrets.toml`.
*   If you accidentally commit your secrets, revoke them immediately from the Google Cloud Console and generate new ones.
