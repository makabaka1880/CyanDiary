#!/opt/anaconda3/envs/diary-client/bin/python
import readline  # For history and autocomplete support
import os
import zipfile
import subprocess
import time
import threading
import requests
import datetime
from dotenv import load_dotenv
from rich.console import Console

# Specify the absolute path to the .env file
dotenv_path = "/Users/makabaka1880/Documents/2025/dev/diary-client/.env"
NODE_SERVER_URL = "http://localhost:8000"

# Load the .env file
load_dotenv(dotenv_path=dotenv_path)

# API URLs
POST_API_URL = os.getenv("DIARY_API_URL") + "/post-entry"
UPDATE_API_URL = os.getenv("DIARY_API_URL") + "/update-entry"
PULL_API_URL = os.getenv("DIARY_API_URL") + "/req-entry"
UPLOAD_API_URL = os.getenv("DIARY_API_URL") + "/upload-assets"
DOWNLOAD_API_URL = os.getenv("DIARY_API_URL") + "/download-assets"
PUSH_API_KEY = os.getenv("DIARY_PUSH_KEY")
PULL_API_KEY = os.getenv("DIARY_PULL_KEY")

# Create a console object to handle output
console = Console()

# Set initial filename globally
filename = datetime.datetime.today().strftime('%Y-%m-%d')  # Set default to today's date
downloads_dir = "downloads"
docs_dir = "/Users/makabaka1880/Documents/2025/dev/diary-client/docs/"  # Directory where the files are now stored

# Setup Readline
readline.set_history_length(1000)
readline.parse_and_bind('tab: complete')
# readline.parse_and_bind("stty erase ^H")


def register_filename():
    """Periodically send the current filename to the Node.js server."""
    global filename
    while True:
        try:
            response = requests.post(f"{NODE_SERVER_URL}/register-filename", json={"filename": filename})
            if response.status_code != 200:
                print(f"Failed to register filename: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with server: {e}")
        
        time.sleep(10)  # Send update every 10 seconds
        
def submit_diary():
    """Submit the diary entry to the API."""
    try:
        # Read the contents from the specified file in the 'docs' directory
        with open(os.path.join(docs_dir, filename, 'entry.md'), "r") as f:
            contents = f.read()

        # Prepare the payload for the API request
        payload = {
            "filename": filename,
            "contents": contents
        }

        # Set the headers for the API request
        headers = {
            "x-api-key": PUSH_API_KEY
        }

        # Send a POST request to submit the diary entry
        response = requests.post(POST_API_URL, json=payload, headers=headers)

        if response.status_code == 201:
            console.print(f"[green]Diary entry '{filename}' submitted successfully![/green]")
        else:
            console.print(f"[red]Failed to submit diary entry ({response.status_code}): {response.text}[/red]")

    except Exception as e:
        console.print(f"[red]Error submitting diary entry: {str(e)}[/red]")

def update_diary():
    """Update the diary entry to the API."""
    try:
        # Read the contents from the specified file in the 'docs' directory
        with open(os.path.join(docs_dir, filename, 'entry.md'), "r") as f:
            contents = f.read()

        # Prepare the payload for the API request
        payload = {
            "filename": filename,
            "contents": contents
        }

        # Set the headers for the API request
        headers = {
            "x-api-key": PUSH_API_KEY
        }

        # Send a POST request to update the diary entry
        response = requests.post(UPDATE_API_URL, json=payload, headers=headers)

        if response.status_code == 201:
            console.print(f"[yellow]Diary entry '{filename}' updated successfully![/yellow]")
        else:
            console.print(f"[red]Failed to update diary entry ({response.status_code}): {response.text}[/red]")

    except Exception as e:
        console.print(f"[red]Error updating diary entry: {str(e)}[/red]")

def pull_diary():
    """Pull a diary entry from the API and save the raw response data as a .md file."""
    try:
        # Send a GET request to pull the diary entry
        response = requests.get(PULL_API_URL, params={"d": filename}, headers={"x-api-key": PULL_API_KEY})

        if response.status_code == 200:
            data = response.json()

            # Get the raw data section from the response
            raw_data = data['data']  # assuming 'data' contains the raw content you want

            # Define the file path
            entry_path = os.path.join(docs_dir, filename, 'entry.md')

            # Check if the directory exists, create it if it doesn't
            directory = os.path.dirname(entry_path)
            if not os.path.exists(directory):
                os.makedirs(directory)
                console.print(f"[blue]Created directory: {directory}[/blue]")

            # Write the raw data directly into a .md file in the 'docs' directory
            with open(entry_path, "w") as f:
                f.write(raw_data)

            console.print(f"[blue]Diary entry saved as {filename}.md in 'docs' directory[/blue]")

        else:
            console.print(f"[red]Failed to fetch diary entry ({response.status_code}): {response.text}[/red]")

    except Exception as e:
        console.print(f"[red]Error fetching diary entry: {str(e)}[/red]")

def edit_diary():
    """Open the diary.md file in the default editor."""
    try:
        console.print(f"[blue]Opening {filename}.md in vim editor...[/blue]")
        subprocess.run(["vim", os.path.join(docs_dir, filename, 'entry.md')])
    except FileNotFoundError:
        console.print("[red]Error: vim is not installed or not found.[/red]")
    except Exception as e:
        console.print(f"[red]Error opening editor: {str(e)}[/red]")

def set_filename(new_filename):
    """Set a new filename for the diary entry."""
    global filename
    if new_filename == '$NOW':
        filename = datetime.datetime.today().strftime('%Y-%m-%d')
    else:
        filename = new_filename
    
    # Check if file exists after changing filename
    entry_path = os.path.join(docs_dir, filename, 'entry.md')
    if not os.path.exists(entry_path):
        console.print(f"[red]Warning: '{entry_path}' does not exist! You may want to create or pull the entry.[/red]")
    else:
        console.print(f"[cyan]Filename set to {filename}.[/cyan]")

def upload_assets():
    """Zip the contents of the assets directory and upload it to the server."""
    assets_dir = os.path.join(docs_dir, filename, 'assets')

    # Check if the assets directory exists
    if not os.path.exists(assets_dir):
        console.print(f"[red]Assets directory for '{filename}' does not exist.[/red]")
        return

    zip_filename = f"{assets_dir}.zip"

    # Create a zip file of the assets directory
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Add each file to the zip archive with relative paths
                zipf.write(file_path, os.path.relpath(file_path, assets_dir))

    # Upload the zip file to the server with correct MIME type
    with open(zip_filename, 'rb') as zipf:
        files = {'zipfile': ('assets.zip', zipf, 'application/zip')}
        headers = {'x-api-key': PUSH_API_KEY}

        try:
            response = requests.post(f"{UPLOAD_API_URL}/{filename}", files=files, headers=headers)

            if response.status_code == 200:
                console.print(f"[green]Assets successfully uploaded to '{filename}'[/green]")
            else:
                console.print(f"[red]Failed to upload assets: {response.status_code}, {response.text}[/red]")
        except Exception as e:
            console.print(f"[red]Error uploading zip file: {str(e)}[/red]")

    # Optionally, remove the local zip file after uploading
    os.remove(zip_filename)

def download_assets():
    """Download the assets ZIP file from the server, save it locally, and unarchive it into the 'assets' folder."""
    zip_filename = docs_dir + 'downloads/assets.zip'  # Define the name of the downloaded ZIP file

    # Construct the URL to download the file from the server
    download_url = f"{DOWNLOAD_API_URL}?d={filename}"  # Adjust the URL according to your server API

    # Send GET request to download the ZIP file
    try:
        response = requests.get(download_url, headers={'x-api-key': PULL_API_KEY})

        if response.status_code == 200:
            # Write the content of the response to a local file
            with open(zip_filename, 'wb') as f:
                f.write(response.content)
            console.print(f"[green]Assets successfully downloaded as '{zip_filename}'[/green]")

            # Unarchive the ZIP file into the assets directory, merging the contents
            assets_dir = os.path.join(docs_dir, filename, 'assets')  # Path to the assets directory

            # Check if assets directory exists, create it if it doesn't
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
                console.print(f"[green]Created assets directory at '{assets_dir}'[/green]")

            # Unarchive the zip file into the 'assets' directory
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                # Extract all contents to the assets directory, merging files
                zip_ref.extractall(assets_dir)
                console.print(f"[green]Assets successfully unarchived into '{assets_dir}'[/green]")

            # Optionally, remove the downloaded zip file after extracting
            os.remove(zip_filename)
            console.print(f"[green]Removed the zip file '{zip_filename}' after extraction.[/green]")

        else:
            console.print(f"[red]Failed to download assets: {response.status_code}, {response.text}[/red]")

    except Exception as e:
        console.print(f"[red]Error downloading assets: {str(e)}[/red]")

def create_diary_entry(name):
    """Create a new diary entry with the specified filename."""
    entry_path = os.path.join(docs_dir, name, 'entry.md')

    # Check if the entry already exists
    if os.path.exists(entry_path):
        console.print(f"[red]Diary entry '{name}' already exists![/red]")
    else:
        # Create the directory if it doesn't exist
        if not os.path.exists(os.path.dirname(entry_path)):
            os.makedirs(os.path.dirname(entry_path))
            console.print(f"[blue]Created directory: {os.path.dirname(entry_path)}[/blue]")

        # Create an empty entry file
        with open(entry_path, "w") as f:
            f.write("")

        console.print(f"[blue]Diary entry '{name}' created successfully![/blue]")
        console.print(f"[blue]You can now edit the entry using the 'edit' command.[/blue]")

def refresh():
    requests.post(f"{NODE_SERVER_URL}/refresh");

def repl():
    """Start the REPL loop."""
    global filename  # Add this line to use the global 'filename'
    while True:
        # Get the user input
        user_input = input(f"[cyan]diary ({filename})[/cyan] > ")

        # Exit condition
        if user_input.lower() == 'exit':
            refresh()
            console.print("[yellow]Exiting...[/yellow]")
            break
        # Handle different commands
        if user_input.lower() == "submit":
            submit_diary()
            refresh()
        elif user_input.lower() == "update":
            update_diary()
            refresh()
        elif user_input.lower() == "pull":
            pull_diary()
            refresh()
        elif user_input.lower() == "edit":
            edit_diary()
            refresh()
        elif user_input.lower() == "ls":
            os.system(f"ls {docs_dir}")
        elif user_input.lower().startswith("file "):
            new_filename = user_input.split(" ", 1)[1]
            set_filename(new_filename)
            refresh()
        elif user_input.lower().startswith("rm "):
            new_filename = user_input.split(" ", 1)[1]
            os.system(f"rm -rf {docs_dir}{new_filename}")
            console.print(f"[red]Removed directory: {docs_dir}{new_filename}[/red]")
            refresh()
        elif user_input.lower().startswith("new "):
            new_filename = user_input.split(" ", 1)[1]
            create_diary_entry(new_filename)
            filename = new_filename
            refresh()
        elif user_input.lower() == "refresh":
            refresh()
        elif user_input.lower() == "upload":
            upload_assets()
            refresh()
        elif user_input.lower() == "download":
            download_assets()
            refresh()
        else:
            console.print(f"[red]Unknown command: {user_input}[/red]")

if __name__ == "__main__":
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
        print(f"[green]Created directory: {downloads_dir}[/green]")
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        print(f"[green]Created directory: {docs_dir}[/green]")
    threading.Thread(target=register_filename, daemon=True).start()
    repl()
