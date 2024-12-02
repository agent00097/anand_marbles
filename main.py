import tkinter as tk
from tkinter import messagebox
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the scope for Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

# Global variable for credentials
creds = None

def authenticate_google_drive():
    """Handles Google Drive authentication and displays files."""
    global creds
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Connect to Google Drive API
        service = build('drive', 'v3', credentials=creds)

        # Fetch and display file names
        results = service.files().list(pageSize=10, fields="files(name)").execute()
        items = results.get('files', [])

        if not items:
            messagebox.showinfo("Google Drive", "No files found.")
        else:
            files = "\n".join(item['name'] for item in items)
            messagebox.showinfo("Google Drive", f"Files:\n{files}")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")

def on_start():
    """Function to handle the Start button click."""
    start_button.config(state=tk.DISABLED)  # Disable the Start button
    end_button.config(state=tk.NORMAL)     # Enable the End button
    print("Start button clicked!")         # Placeholder action
    authenticate_google_drive()

def on_end():
    """Function to handle the End button click."""
    end_button.config(state=tk.DISABLED)   # Disable the End button
    start_button.config(state=tk.NORMAL)  # Enable the Start button
    print("End button clicked!")           # Placeholder action

# Create the main window
root = tk.Tk()
root.title("Simple GUI")

# Create the Start button
start_button = tk.Button(root, text="Start", command=on_start)
start_button.pack(pady=10)

# Create the End button (disabled by default)
end_button = tk.Button(root, text="End", command=on_end, state=tk.DISABLED)
end_button.pack(pady=10)


if __name__=="__main__":

    # Things to do in this order
    # Open a web browser to be connected to the google account (Authentication)
    # Using a hard encoded link download the latest files for tally
    # Save the current tally files to another place in google drive
    # Move the downloaded copy to the working space in tally
    root.mainloop()

    pass