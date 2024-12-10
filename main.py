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

        def recursive_download(folder_id, current_path):
            """Recursively download files and folders."""
            try:
                results = self.drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields="files(id, name, mimeType)",
                ).execute()

                items = results.get('files', [])
                for item in items:
                    file_id = item['id']
                    file_name = item['name']
                    mime_type = item['mimeType']

                    if mime_type == 'application/vnd.google-apps.folder':
                        subfolder_path = os.path.join(current_path, file_name)
                        os.makedirs(subfolder_path, exist_ok=True)
                        recursive_download(file_id, subfolder_path)
                    else:
                        file_path = os.path.join(current_path, file_name)
                        request = self.drive_service.files().get_media(fileId=file_id)
                        with open(file_path, 'wb') as f:
                            downloader = MediaIoBaseDownload(f, request)
                            done = False
                            while not done:
                                _, done = downloader.next_chunk()

            except HttpError as error:
                print(f"Error downloading files: {error}")

        # Start recursive download
        recursive_download(folder_id, self.tmp_folder)

        # Update the progress bar
        self.update_progress_bar(100)

        # Notify the user of successful download
        messagebox.showinfo(
            "Download Complete",
            f"All files and folders have been downloaded successfully.\nLocation: {self.tmp_folder}"
        )

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
        """Upload the contents of the `tmp` folder to a cloud bucket."""
        pass  # Assume this function is implemented correctly

    def check_and_create_folder(self, folder_name):
        """Check if a folder exists in Google Drive, and create it if it doesn't."""
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            else:
                folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
                return folder.get('id')
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None

    def upload_to_drive(self, folder_id, local_path=None):
        """Upload files and folders from local path to Google Drive."""
        pass  # Assume this function is implemented correctly

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
