import os
import fnmatch
import sys
import requests
import time


def parse_env_file(file_path):
    env_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
    return env_dict

env_dict=parse_env_file("./liepa_ausys.env")

def transcription(wav_path):
    print(wav_path)
    transcription_id=send_file_to_server(wav_path)
    reg_result = 0
    while_timeout = time.time() + 120
    transcription_status=""
    perf={"Diarization":0,"ResultMake":0,"ResultMake":0, "COMPLETED":0, "Transcription":0}
    while transcription_status != "COMPLETED" and time.time() < while_timeout:
        time.sleep(1)
        transcription_status = check_transription_status(transcription_id)
        print("transcription_status", transcription_status, transcription_status != "COMPLETED" )
        perf[transcription_status]=perf[transcription_status]+1
    transcription_lat=get_transription_lat(transcription_id)
    print(perf)
    f = open(wav_path+".txt", "w")
    f.write(transcription_lat)
    f.close()
        

def print_wav_files_in_directory(directory):
    try:
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path) and fnmatch.fnmatch(entry, "*.wav"):
                transcription(full_path)
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found.")
    except PermissionError:
        print(f"Error: Permission denied for accessing '{directory}'.")

def send_file_to_server(file_path):
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    with open(file_path, 'rb') as file:
        files = {'file': (file_path, file, 'multipart/form-data')}
        data = {'recognizer': "ben"}
        headers = {'Authorization': f'Basic {auth}'}
        response = requests.post(url + "/transcriber/upload", files=files, data=data, headers=headers)
        print(f"Server response: {response.status_code}, {response.text}")
        response_json = response.json()
        #print(response_json)
        transcription_id=response_json["id"]
        return transcription_id


def check_transription_status(transcription_id):
    print("------------------- check_transription_status -------------------")
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    headers = {'Authorization': f'Basic {auth}'}
    response = requests.get(url+"/status.service/status/"+transcription_id,  headers=headers)
    #print(f"Server response: {response.status_code}, {response.text}")
    response_json = response.json()
    #print(response_json)
    error=response_json["error"]
    status=response_json["status"]
    print("Error: " + error + "; status: " + status)
    return status

def get_transription_lat(transcription_id):
    print("------------------- get_transription_lat -------------------")
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    headers = {'Authorization': f'Basic {auth}'}
    response = requests.get(url+"/result.service/result/"+transcription_id+"/lat.restored.txt",  headers=headers)
    print(f"Server response: {response.status_code}, {response.text}")
    return response.text
        





if __name__ == "__main__":
    #directory = "./wav"
    directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")
    print(env_dict)
    print_wav_files_in_directory(directory)