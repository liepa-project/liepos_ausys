#!/usr/bin/env python
import os
import fnmatch
import requests
import time
import logging
import re


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



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
liepa_ausys_processing_timeout_sec=3600 #1h
liepa_ausys_processing_poll_sec=3 #1h

def transcription(wav_path):
    wav_length_in_sec=get_wav_file_length(wav_path)
    logging.info(f"Sound files: {wav_path}. Length: {wav_length_in_sec} s")
    if(wav_length_in_sec == 0):
        logging.error("Error. File length is 0")
        return
    transcription_id=send_file_to_server(wav_path)
    if(transcription_id == ""):
        logging.error("Error. Transcription ID not found")
        return
    
    while_timeout = time.time() + liepa_ausys_processing_timeout_sec
    transcription_status=""
    processing_time_per_status={}#"Diarization":0,"ResultMake":0,"ResultMake":0, "COMPLETED":0, "Transcription":0
    while transcription_status != "COMPLETED" and time.time() < while_timeout:
        time.sleep(liepa_ausys_processing_poll_sec)
        transcription_status = check_transription_status(transcription_id)
        #print("transcription_status", transcription_status, transcription_status != "COMPLETED" )
        processing_time = processing_time_per_status.get(transcription_status, 0);
        processing_time_per_status[transcription_status]=processing_time+liepa_ausys_processing_poll_sec
        
        print(" transcription_status: " + transcription_status + " " + str(processing_time_per_status[transcription_status]), end='\r' )
    transcription_lat=get_transription_lat(transcription_id)
    
    if(transcription_lat == ""):
        logging.error("Error. Transcription lat not found")
        return
    total_processing_time_in_sec = sum(processing_time_per_status.values())
    logging.info(f"Processing  took seconds: {total_processing_time_in_sec} (Ratio {total_processing_time_in_sec/wav_length_in_sec}). Breakdown:{str(processing_time_per_status)}")
    output_file_path = re.sub('wav$', 'lat', wav_path)
    # f = open(output_file_path, "w")
    with open(output_file_path, "w", encoding="utf-8") as f:
        logging.info(f"Wring result to {output_file_path}")
        f.write(transcription_lat)
        

def transcribe_wav_files_in_directory(directory):
    try:
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path) and fnmatch.fnmatch(entry, "*.wav"):
                transcription(full_path)
    except FileNotFoundError:
        logging.error(f"Error: Directory '{directory}' not found.")
    except PermissionError:
        logging.error(f"Error: Permission denied for accessing '{directory}'.")

def send_file_to_server(file_path):
    logging.debug("------------------- send_file_to_server -------------------")
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    with open(file_path, 'rb') as file:
        files = {'file': (file_path, file, 'multipart/form-data')}
        data = {'recognizer': "ben"}
        headers = {'Authorization': f'Basic {auth}'}
        send_url=url + "/transcriber/upload"
        # logging.debug(f"Sending request to: {send_url} ")
        response = requests.post(send_url, files=files, data=data, headers=headers)
        transcription_id=""
        if(response.ok):
            response_json = response.json()
            #print(response_json)
            transcription_id=response_json["id"]
            logging.info(f'transcription id:{transcription_id}')
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
        return transcription_id


def check_transription_status(transcription_id):
    logging.debug("------------------- check_transription_status -------------------")
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    headers = {'Authorization': f'Basic {auth}'}
    status_url=url+"/status.service/status/"+transcription_id
    # print(f"Sending request to: {status_url} ")
    response = requests.get(status_url,  headers=headers)
    #print(f"Server response: {response.status_code}, {response.text}")
    error=""
    status="Failed"# default value
    if(response.ok):
        response_json = response.json()
        #print(response_json)
        error=response_json["error"]
        status=response_json["status"]
        if(error != ""):
            logging.error(f"Error: {error} during {status}")
    else:
        logging.debug(f"Error: Server response: {response.status_code}, {response.text}")
        
    return status

def get_transription_lat(transcription_id):
    logging.debug("------------------- get_transription_lat -------------------")
    url=env_dict["liepa_ausys_url"]
    auth=env_dict["liepa_ausys_auth"]
    headers = {'Authorization': f'Basic {auth}'}
    lat_result_url=url+"/result.service/result/"+transcription_id+"/lat.restored.txt"
    # logging.debug(f"Sending request to: {lat_result_url} ")
    response = requests.get(lat_result_url,  headers=headers)
    lat_text=""
    if(response.ok):
        lat_text=response.text
    else:
        logging.error(f"Server response: {response.status_code}, {response.text}")
    return lat_text
        

def get_wav_file_length(file_path):
    with open(file_path, 'rb') as f:
        # Read the header information
        f.seek(24)  # Start of Sample Rate (byte 24)
        sample_rate = int.from_bytes(f.read(4), 'little')

        f.seek(40)  # Start of Data Subchunk size (byte 40)
        data_size = int.from_bytes(f.read(4), 'little')

        # WAV file length in seconds
        length_seconds = data_size / (sample_rate * 2)  # Assuming 16-bit audio (2 bytes per sample)
        return length_seconds


if __name__ == "__main__":
    #directory = "./wav"
    # print(env_dict)
    param_error=False
    if env_dict["liepa_ausys_wav_path"] == "":
        logging.info("liepa_ausys_wav_path is not set in liepa_ausys.env")
        param_error=True
    if env_dict["liepa_ausys_url"] == "":
        logging.info("liepa_ausys_url is not set in liepa_ausys.env")
        param_error=True
    if env_dict["liepa_ausys_auth"] == "":
        logging.info("liepa_ausys_auth is not set in liepa_ausys.env")
        param_error=True
    if param_error:
        logging.error("Error occured. Exiting...")
    else:
        directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")
        transcribe_wav_files_in_directory(directory)
