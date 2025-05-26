import streamlit as st
from modules import data_loader # Assuming data_loader.py is in a 'modules' folder at the root
import uuid # For generating unique IDs

def show_teacher_page():
    st.title("Teacher/Parent - Data Upload Portal")

    # --- Google Drive Authentication and Service ---
    drive_service = data_loader.get_drive_service()

    if not drive_service:
        st.warning("Please authenticate with Google Drive to use all features of this page.")
        # The get_drive_service() function in data_loader should handle showing auth link/input
        st.stop() # Stop further execution if no service
    
    st.success("Successfully connected to Google Drive!")
    st.markdown("---")

    # --- Competition Type Selection ---
    competition_types = ["General", "ARIMA", "ARMA", "SARIMA", "Classification", "Regression"]
    selected_competition_type = st.selectbox(
        "Select Competition Type:",
        options=competition_types,
        index=0
    )
    st.markdown("---")

    # --- File Uploaders ---
    st.subheader(f"Upload Data for '{selected_competition_type}' Competition")
    uploaded_files = data_loader.display_file_uploaders(selected_competition_type)
    
    # Basic check: Ensure train file is uploaded before allowing Drive upload
    can_proceed_with_upload = uploaded_files.get('train') is not None
    
    st.markdown("---")

    # --- Upload to Google Drive Button & Logic ---
    if st.button("Process and Upload Files to Google Drive", disabled=not can_proceed_with_upload):
        if not can_proceed_with_upload:
            st.error("Please upload at least the training data CSV before proceeding.")
        else:
            # For simplicity, using a combination of competition type and a UUID part for unique_id
            # In a real app, this might come from a form or database
            submission_id = f"{selected_competition_type.lower().replace(' ', '_')}_{str(uuid.uuid4())[:8]}"
            st.write(f"Generated Submission ID: `{submission_id}`")

            with st.spinner(f"Uploading files to Google Drive with ID: {submission_id}..."):
                drive_file_ids = data_loader.upload_csvs_to_drive(
                    uploaded_files=uploaded_files,
                    unique_id=submission_id,
                    drive_service=drive_service
                )

            if drive_file_ids:
                st.success("File upload process completed!")
                
                train_file_id = drive_file_ids.get('train')
                if train_file_id:
                    with st.spinner("Generating shareable link for training data..."):
                        train_link = data_loader.get_drive_shareable_link(train_file_id, drive_service)
                        if train_link:
                            st.markdown(f"**Train Data Link:** [{train_link}]({train_link})")
                        else:
                            st.error("Could not generate shareable link for training data.")
                
                test_inputs_id = drive_file_ids.get('test_inputs')
                if test_inputs_id: # Will be None for ARIMA types etc.
                    with st.spinner("Generating shareable link for test inputs data..."):
                        test_inputs_link = data_loader.get_drive_shareable_link(test_inputs_id, drive_service)
                        if test_inputs_link:
                            st.markdown(f"**Test Inputs Data Link:** [{test_inputs_link}]({test_inputs_link})")
                        else:
                            st.error("Could not generate shareable link for test inputs data.")
                
                # Note: Test Outputs are usually not shared via link in this context, but uploaded.
                test_outputs_id = drive_file_ids.get('test_outputs')
                if test_outputs_id:
                     st.info(f"Test outputs CSV (`test_outputs_{submission_id}.csv`) uploaded with File ID: {test_outputs_id}")

            else:
                st.error("File upload to Google Drive failed. Check previous error messages.")
    elif not can_proceed_with_upload:
         st.info("Please upload the training data CSV to enable the 'Process and Upload' button.")


# This allows running this page directly for testing if needed,
# though it's meant to be a page in a multipage app.
if __name__ == "__main__":
    # To make st.secrets work when running directly, you might need to ensure Streamlit context
    # This is more for quick testing.
    # Typically, you'd run `streamlit run app.py`
    show_teacher_page()
