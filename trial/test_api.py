import requests
import time
import os

API_BASE_URL = "http://127.0.0.1:8000/api/v1"
API_KEY = "sk_test_key_1234567890"
FILE_PATH = "table.pdf"

def test_api():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    # 1. Create Job
    print(f"Uploading {FILE_PATH}...")
    if not os.path.exists(FILE_PATH):
        print(f"Error: {FILE_PATH} not found in {os.getcwd()}")
        return

    with open(FILE_PATH, "rb") as f:
        files = {"file": (FILE_PATH, f, "application/pdf")}
        response = requests.post(f"{API_BASE_URL}/jobs", headers=headers, files=files)
    
    if response.status_code != 201:
        print(f"Failed to create job: {response.status_code} {response.text}")
        return
    
    job_id = response.json()["job_id"]
    print(f"Job created! ID: {job_id}")
    
    # 2. Poll for status
    while True:
        status_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}", headers=headers)
        if status_response.status_code != 200:
            print(f"Failed to get status: {status_response.status_code} {status_response.text}")
            return
            
        status_data = status_response.json()
        status = status_data["status"]
        print(f"Current status: {status}")
        
        if status == "COMPLETED":
            break
        elif status == "FAILED":
            print(f"Job failed! Error: {status_data.get('error_message')}")
            return
        
        time.sleep(1)
    
    # 3. Get download URL
    download_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/download", headers=headers)
    if download_response.status_code != 200:
        print(f"Failed to get download URL: {download_response.status_code} {download_response.text}")
        return
        
    download_url = download_response.json()["download_url"]
    
    # Handle local download URL
    if download_url.startswith("/"):
        download_url = f"http://127.0.0.1:8000{download_url}"
        
    print(f"Downloading from {download_url}...")
    
    # 4. Download file
    file_response = requests.get(download_url)
    output_filename = f"result_{job_id}.xlsx"
    with open(output_filename, "wb") as f:
        f.write(file_response.content)
    
    print(f"Saved result to {output_filename}")

if __name__ == "__main__":
    # Change to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    test_api()
