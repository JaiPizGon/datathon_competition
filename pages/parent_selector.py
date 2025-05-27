import streamlit as st
from modules import data_loader # Assuming data_loader.py is in a 'modules' folder at the root

def show_parent_selector_page():
    st.set_page_config(layout="wide") # Optional: Use wide layout for more space
    st.title("Datathon Setup: Parent Selector")
    st.write("This page allows you to select or upload datasets and configure the datathon type.")
    st.markdown("---")

    # --- 1. Google Drive Authentication ---
    st.header("Step 1: Connect to Google Drive")
    drive_service = data_loader.get_drive_service()

    if not drive_service:
        st.warning("Please authenticate with Google Drive to proceed.")
        # data_loader.get_drive_service() should display auth instructions/link
        st.stop() # Stop further execution if no service
    
    st.success("Successfully connected to Google Drive!")
    st.markdown("---")

    # Placeholder for upcoming sections
    st.header("Step 2: Select or Upload Dataset")

    # Part A: Select Existing Dataset
    st.subheader("A. Select Existing Dataset from Google Drive")
    
    # Initialize session state for selected dataset if not already present
    if 'selected_drive_dataset_info' not in st.session_state:
        st.session_state.selected_drive_dataset_info = None

    csv_files_list = data_loader.list_csv_files_from_drive(drive_service)

    if csv_files_list:
        dataset_options = {f"{file_info['name']} (ID: {file_info['id']})": file_info for file_info in csv_files_list}
        placeholder_option = "Select a dataset..."
        
        # Create a list of display names for the selectbox
        display_options = [placeholder_option] + list(dataset_options.keys())
        
        selected_display_name = st.selectbox(
            "Choose an existing dataset:",
            options=display_options,
            index=0 # Default to placeholder
        )

        if selected_display_name != placeholder_option:
            st.session_state.selected_drive_dataset_info = dataset_options[selected_display_name]
            # Clear any previous test file IDs when main dataset changes
            if 'current_test_inputs_id' in st.session_state: del st.session_state.current_test_inputs_id
            if 'current_test_outputs_id' in st.session_state: del st.session_state.current_test_outputs_id
            st.success(f"You selected: '{st.session_state.selected_drive_dataset_info['name']}' "
                       f"(ID: {st.session_state.selected_drive_dataset_info['id']})")
        else:
            st.session_state.selected_drive_dataset_info = None # Reset if placeholder selected
            if 'current_test_inputs_id' in st.session_state: del st.session_state.current_test_inputs_id
            if 'current_test_outputs_id' in st.session_state: del st.session_state.current_test_outputs_id
            # st.info("No dataset selected from Drive yet.")

    else:
        st.info("No CSV datasets found in the configured Google Drive folder. You can upload a new one below.")

    st.markdown("---") # Visual separator
    st.subheader("B. Upload New Main Dataset CSV")
    
    with st.expander("Upload a new dataset to be used as the main/training data", expanded=False):
        new_dataset_name = st.text_input(
            "Enter a name for this new dataset (e.g., 'October_Sales_Data'):", 
            key="new_dataset_name_input" # Unique key for input field
        )
        
        uploaded_main_csv = st.file_uploader(
            "Upload the main CSV file:", 
            type=['csv'], 
            key="main_csv_uploader" # Unique key for uploader
        )

        if st.button("Upload Named Dataset to Drive", key="upload_new_dataset_button"):
            if not new_dataset_name:
                st.error("Please provide a name for the new dataset.")
            elif not uploaded_main_csv:
                st.error("Please upload a CSV file.")
            else:
                # Use the dataset name for the 'unique_id' for Drive naming, 
                # and a generic key for the uploaded_files dictionary.
                # Sanitize new_dataset_name for use in filename if needed (e.g., replace spaces with underscores)
                safe_dataset_name = new_dataset_name.replace(" ", "_").lower()
                
                # Let's simplify: Upload this as 'train_<safe_dataset_name>.csv'
                # This makes it directly usable as a training set.
                files_to_upload_for_drive = {'train': uploaded_main_csv}

                with st.spinner(f"Uploading '{new_dataset_name}' to Google Drive..."):
                    upload_results = data_loader.upload_csvs_to_drive(
                        uploaded_files=files_to_upload_for_drive,
                        unique_id=safe_dataset_name, # This will result in train_safe_dataset_name.csv
                        drive_service=drive_service
                    )

                uploaded_file_id = upload_results.get('train')
                if uploaded_file_id:
                    st.success(f"Dataset '{new_dataset_name}' uploaded successfully as 'train_{safe_dataset_name}.csv' with ID: {uploaded_file_id}.")
                    # Clear the uploader and text input after successful upload
                    st.session_state.new_dataset_name_input = ""
                    # Clearing file uploader is tricky, usually done by rerunning or complex session state.
                    # For now, a rerun might be implicitly handled by Streamlit.
                    st.info("Dataset list will refresh on next interaction or page reload.")
                    # Ideally, trigger a rerun or update the list of datasets shown above.
                    # For simplicity, we'll rely on user selecting it from the refreshed list.
                else:
                    st.error(f"Failed to upload '{new_dataset_name}'. Check logs for details.")

    # Part C: Manage associated files if a dataset is selected from Drive
    if st.session_state.get('selected_drive_dataset_info'):
        selected_info = st.session_state.selected_drive_dataset_info
        st.markdown("---") # Visual separator before managing selected dataset
        st.subheader(f"C. Manage Associated Test Files for: '{selected_info['name']}'")
        
        # Display shareable link for the selected main dataset
        with st.spinner(f"Fetching shareable link for {selected_info['name']}..."):
            link = data_loader.get_drive_shareable_link(selected_info['id'], drive_service)
            if link:
                st.markdown(f"**Link to main dataset '{selected_info['name']}':** [{link}]({link})")
            else:
                st.error(f"Could not retrieve shareable link for {selected_info['name']}.")

        st.write("You can now upload corresponding test input and test output files for this dataset.")

        # File uploaders for test data
        uploaded_test_inputs_csv = st.file_uploader(
            f"Upload Test Inputs CSV for '{selected_info['name']}' (optional):",
            type=['csv'],
            key=f"test_inputs_uploader_{selected_info['id']}" # Keyed to selected dataset
        )
        uploaded_test_outputs_csv = st.file_uploader(
            f"Upload Test Outputs CSV for '{selected_info['name']}' (optional):",
            type=['csv'],
            key=f"test_outputs_uploader_{selected_info['id']}" # Keyed to selected dataset
        )

        if st.button(f"Upload Test Files for '{selected_info['name']}'", key=f"upload_test_files_button_{selected_info['id']}"):
            if not uploaded_test_inputs_csv and not uploaded_test_outputs_csv:
                st.warning("No test files were uploaded. Nothing to do.")
            else:
                files_to_upload_for_drive = {}
                if uploaded_test_inputs_csv:
                    files_to_upload_for_drive['test_inputs'] = uploaded_test_inputs_csv
                if uploaded_test_outputs_csv:
                    files_to_upload_for_drive['test_outputs'] = uploaded_test_outputs_csv
                
                # Use the original selected dataset's name or ID as the 'unique_id' base
                # The actual filename on Drive will be test_inputs_<unique_id>.csv etc.
                # Sanitize the name part of the selected dataset for use in unique_id
                base_unique_id = selected_info['name'].replace(" ", "_").lower()
                # Remove .csv if present, and other common extensions, to make a clean base ID
                for ext in ['.csv', '.xlsx', '.xls']: # Add other extensions if needed
                    if base_unique_id.endswith(ext):
                        base_unique_id = base_unique_id[:-len(ext)]
                
                with st.spinner(f"Uploading test files for '{selected_info['name']}'..."):
                    upload_results = data_loader.upload_csvs_to_drive(
                        uploaded_files=files_to_upload_for_drive,
                        unique_id=base_unique_id, 
                        drive_service=drive_service
                    )

                if upload_results:
                    st.success("Test file upload process completed.")
                    if 'test_inputs' in upload_results and upload_results['test_inputs']:
                        test_inputs_id = upload_results['test_inputs']
                        st.session_state.current_test_inputs_id = test_inputs_id # STORE HERE
                        with st.spinner("Generating shareable link for test inputs..."):
                            link_ti = data_loader.get_drive_shareable_link(test_inputs_id, drive_service)
                            if link_ti:
                                st.markdown(f"**Test Inputs ('test_inputs_{base_unique_id}.csv') Link:** [{link_ti}]({link_ti})")
                    
                    if 'test_outputs' in upload_results and upload_results['test_outputs']:
                        test_outputs_id = upload_results['test_outputs']
                        st.session_state.current_test_outputs_id = test_outputs_id # STORE HERE
                        # Typically test_outputs are not shared via link but ID is good to have
                        st.info(f"Test Outputs ('test_outputs_{base_unique_id}.csv') CSV uploaded with File ID: {test_outputs_id}")
                else:
                    st.error("Some test files may not have uploaded successfully. Check logs.")
    
    st.markdown("---")

    st.header("Step 3: Select Datathon Type")

    # Initialize session state for datathon type if not already present
    if 'datathon_type' not in st.session_state:
        st.session_state.datathon_type = None

    datathon_type_options = ["Regression", "Classification", "Forecasting", "SARIMA"]
    
    selected_type = st.selectbox(
        "Choose the type of datathon:",
        options=datathon_type_options,
        index=0 if st.session_state.datathon_type is None else datathon_type_options.index(st.session_state.datathon_type) # Keep previous selection
    )

    if selected_type:
        st.session_state.datathon_type = selected_type
        st.info(f"Datathon type selected: **{st.session_state.datathon_type}**")
    else:
        # Should not happen with selectbox unless options are empty or manipulated
        st.session_state.datathon_type = None 
        st.warning("No datathon type selected.")

    st.markdown("---")
    
    st.header("Step 4: Confirm Setup")

    # Initialize final datathon session state keys if not present
    for key in ['datathon_train_file_id', 'datathon_train_file_name', 
                'datathon_test_inputs_file_id', 'datathon_test_outputs_file_id', 
                'datathon_type_final']: # Use _final to avoid conflict with Step 3's datathon_type during selection
        if key not in st.session_state:
            st.session_state[key] = None

    if st.button("✅ Confirm Datathon Setup and Save Choices"):
        valid_setup = True
        
        # 1. Check for selected main/train dataset
        if st.session_state.get('selected_drive_dataset_info'):
            main_dataset_info = st.session_state.selected_drive_dataset_info
            st.session_state.datathon_train_file_id = main_dataset_info['id']
            st.session_state.datathon_train_file_name = main_dataset_info['name']
        else:
            st.error("❌ Error: No main dataset selected. Please select or upload a main dataset in Step 2.")
            valid_setup = False
            
        # 2. Check for datathon type
        if st.session_state.get('datathon_type'):
            st.session_state.datathon_type_final = st.session_state.datathon_type
        else:
            st.error("❌ Error: No datathon type selected. Please select a type in Step 3.")
            valid_setup = False
            
        # 3. Retrieve associated test file IDs (these were set by the "Upload Test Files" button in Step 2 Part C)
        st.session_state.datathon_test_inputs_file_id = st.session_state.get('current_test_inputs_id')
        st.session_state.datathon_test_outputs_file_id = st.session_state.get('current_test_outputs_id')

        if valid_setup:
            st.success("🎉 Datathon Setup Confirmed and Saved! 🎉")
            st.balloons()
            
            st.markdown("### Summary of Configuration:")
            st.write(f"- **Train Dataset:** {st.session_state.datathon_train_file_name} (ID: {st.session_state.datathon_train_file_id})")
            if st.session_state.datathon_test_inputs_file_id:
                st.write(f"- **Test Inputs ID:** {st.session_state.datathon_test_inputs_file_id}")
            else:
                st.write("- **Test Inputs:** Not provided.")
            if st.session_state.datathon_test_outputs_file_id:
                st.write(f"- **Test Outputs ID:** {st.session_state.datathon_test_outputs_file_id}")
            else:
                st.write("- **Test Outputs:** Not provided.")
            st.write(f"- **Datathon Type:** {st.session_state.datathon_type_final}")
            
            # Clear intermediate selections after successful confirmation
            if 'selected_drive_dataset_info' in st.session_state: del st.session_state.selected_drive_dataset_info
            if 'current_test_inputs_id' in st.session_state: del st.session_state.current_test_inputs_id
            if 'current_test_outputs_id' in st.session_state: del st.session_state.current_test_outputs_id
            # Keep st.session_state.datathon_type so Step 3 shows current selection if user re-confirms
            
        else:
            st.error("Configuration incomplete. Please address the errors above and try again.")

    st.markdown("---")
    # Optional: Show current session state for debugging
    # if st.checkbox("Show current datathon session state (for debugging)"):
    #     debug_state = {
    #         'datathon_train_file_id': st.session_state.get('datathon_train_file_id'),
    #         'datathon_train_file_name': st.session_state.get('datathon_train_file_name'),
    #         'datathon_test_inputs_file_id': st.session_state.get('datathon_test_inputs_file_id'),
    #         'datathon_test_outputs_file_id': st.session_state.get('datathon_test_outputs_file_id'),
    #         'datathon_type_final': st.session_state.get('datathon_type_final')
    #     }
    #     st.json(debug_state)

# This allows running this page directly for testing if needed,
# though it's meant to be a page in a multipage app.
if __name__ == "__main__":
    # This is more for quick testing.
    # Typically, you'd run `streamlit run app.py`
    # Ensure you have secrets.toml configured for Drive auth to work.
    show_parent_selector_page()
