import os
import googleapiclient
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import tkinter as tk
from tkinter import messagebox
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from tkinter import ttk
import datetime


class GoogleDriveApp:
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("Google Drive Integration")

        # Initialize credentials
        self.creds = None

        # Temporary folder setup
        self.tmp_folder = os.path.join(os.getcwd(), "tmp")
        if not os.path.exists(self.tmp_folder):
            os.makedirs(self.tmp_folder)

        # Create Start button
        self.start_button = tk.Button(root, text="Start", command=self.on_start)
        self.start_button.pack(pady=10)

        # Create End button (disabled by default)
        self.end_button = tk.Button(root, text="End", command=self.on_end, state=tk.DISABLED)
        self.end_button.pack(pady=10)

        # Progress bar for tracking download/upload progress
        self.progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(pady=10)

        self.folder_id = ""

    def update_progress_bar(self, value):
        """Update the progress bar value and refresh the UI."""
        self.progress["value"] = value
        self.root.update_idletasks()

    def download_files_from_folder(self, folder_id):
        """
        Download all files and folders from a given Google Drive folder ID.
        """
        from googleapiclient.errors import HttpError

        # Ensure the tmp folder exists
        os.makedirs(self.tmp_folder, exist_ok=True)

        try:
            # List all items in the folder
            results = self.drive_service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id, name, mimeType)",
            ).execute()

            items = results.get('files', [])
            if not items:
                print(f"No files found in folder {folder_id}.")
                return

            # Iterate through items in the folder
            for item in items:
                file_id = item['id']
                file_name = item['name']
                mime_type = item['mimeType']

                # Handle folders recursively
                if mime_type == 'application/vnd.google-apps.folder':
                    print(f"Found folder: {file_name}")
                    subfolder_path = os.path.join(self.tmp_folder, file_name)
                    os.makedirs(subfolder_path, exist_ok=True)
                    # Recursive call for the subfolder
                    self.download_files_from_folder(file_id)
                else:
                    print(f"Downloading file: {file_name}")
                    try:
                        file_path = os.path.join(self.tmp_folder, file_name)
                        request = self.drive_service.files().get_media(fileId=file_id)
                        with open(file_path, 'wb') as f:
                            downloader = googleapiclient.http.MediaIoBaseDownload(f, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                                print(f"Download progress for {file_name}: {int(status.progress() * 100)}%")
                    except HttpError as error:
                        print(f"Error downloading file {file_name}: {error}")

            # Notify the user of successful download
            messagebox.showinfo(
                "Download Complete",
                f"Files have been downloaded successfully.\nLocation: {self.tmp_folder}"
            )

        except HttpError as error:
            print(f"Error listing files in folder {folder_id}: {error}")
            messagebox.showerror("Error", f"An error occurred while downloading: {error}")

    def on_start(self):
        """Handle Start button click."""
        self.start_button.config(state=tk.DISABLED)
        self.end_button.config(state=tk.NORMAL)
        self.authenticate_google_drive()
        self.folder_id = self.check_and_create_folder("app_data")
        self.download_files_from_folder(self.folder_id)

    def on_end(self):
        """Handle the end button action."""
        response = messagebox.askyesno(
            "Exit Confirmation",
            "Make sure everything is saved and closed before exiting."
        )

        if not response:  # If No is selected
            print("User chose to continue using the app.")
            return

        try:
            # Step 1: Upload `tmp` folder to the cloud bucket
            self.upload_tmp_to_bucket()

            # Step 2: Upload `tmp` folder content to Google Drive's `app_data`
            self.upload_to_drive(self.folder_id)

            # Step 3: Notify user and exit
            messagebox.showinfo("Completed", "Everything done.")
            self.root.quit()  # Exit the application

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def upload_tmp_to_bucket(self):
        """
        Recursively upload the contents of the `tmp` folder, including files and subfolders, to the cloud bucket.
        """
        from google.cloud import storage
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        if not self.creds.valid and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())

        credentials = Credentials(
            token=self.creds.token,
            refresh_token=self.creds.refresh_token,
            token_uri=self.creds.token_uri,
            client_id=self.creds.client_id,
            client_secret=self.creds.client_secret,
            scopes=self.creds.scopes,
        )
        storage_client = storage.Client(credentials=credentials, project="your_project_id")

        bucket_name = "ama_backup_97"
        bucket = storage_client.bucket(bucket_name)

        def upload_recursive(local_path, bucket_path=""):
            for item in os.listdir(local_path):
                item_path = os.path.join(local_path, item)
                if os.path.isdir(item_path):  # If it's a folder
                    new_bucket_path = f"{bucket_path}/{item}" if bucket_path else item
                    upload_recursive(item_path, new_bucket_path)
                else:  # If it's a file
                    blob = bucket.blob(f"{bucket_path}/{item}" if bucket_path else item)
                    blob.upload_from_filename(item_path)
                    print(f"Uploaded {item_path} to bucket as {blob.name}")

        # Start recursive upload from tmp folder
        upload_recursive(self.tmp_folder)

    def check_and_create_folder(self, folder_name):
        """Check if a folder exists in Google Drive, and create it if it doesn't."""
        try:
            service = build('drive', 'v3', credentials=self.creds)
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                print(f"Folder '{folder_name}' exists with ID: {folder_id}")
                return folder_id
            else:
                folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
                print(f"Folder '{folder_name}' created with ID: {folder_id}")
                return folder_id
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None

    def upload_to_drive(self, folder_id, local_path=None):
        """
        Recursively uploads files and folders from the local path to the specified Google Drive folder.
        """
        if local_path is None:
            local_path = self.tmp_folder

        try:
            service = build('drive', 'v3', credentials=self.creds)

            # Traverse through all files and folders in the local directory
            for item in os.listdir(local_path):
                item_path = os.path.join(local_path, item)

                if os.path.isdir(item_path):  # If the item is a folder
                    # Check if the folder already exists in Google Drive
                    query = f"mimeType='application/vnd.google-apps.folder' and name='{item}' and '{folder_id}' in parents"
                    results = service.files().list(
                        q=query,
                        spaces='drive',
                        fields='files(id, name)',
                        pageSize=1
                    ).execute()
                    folders = results.get('files', [])
                    if folders:
                        subfolder_id = folders[0]['id']
                    else:
                        # Create a new folder in Google Drive
                        folder_metadata = {'name': item, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [folder_id]}
                        folder = service.files().create(body=folder_metadata, fields='id').execute()
                        subfolder_id = folder.get('id')
                        print(f"Folder '{item}' created in Google Drive with ID: {subfolder_id}.")

                    # Recur to upload contents of the subfolder
                    self.upload_to_drive(subfolder_id, item_path)

                else:  # If the item is a file
                    print(f"Uploading file: {item} to Google Drive.")
                    file_metadata = {'name': item, 'parents': [folder_id]}
                    media = MediaFileUpload(item_path, resumable=True)
                    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        except Exception as e:
            print(f"Error uploading to Google Drive: {e}")

    def authenticate_google_drive(self):
        """Handles Google Drive authentication."""
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": "971877310369-ai2k5mom7223i6fbpmplto3145vh0q9q.apps.googleusercontent.com",
                    "project_id": "command-line-project-429810",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "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",
                    "redirect_uris": ["http://localhost"]
                }
            },
            [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/devstorage.read_write"
            ]
        )
        self.creds = flow.run_local_server(port=0)
        self.drive_service = build('drive', 'v3', credentials=self.creds)


def main():
    """Main function to start the app."""
    root = tk.Tk()
    app = GoogleDriveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
