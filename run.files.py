import os
import fnmatch
import sys
import requests
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



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
    logging.info(f"Sound files: {wav_path}")
    transcription_id=send_file_to_server(wav_path)
    if(transcription_id == ""):
        logging.error("Error. Transcription ID not found")
        return
    reg_result = 0
    while_timeout = time.time() + 120
    transcription_status=""
    perf={"Diarization":0,"ResultMake":0,"ResultMake":0, "COMPLETED":0, "Transcription":0}
    while transcription_status != "COMPLETED" and time.time() < while_timeout:
        time.sleep(1)
        transcription_status = check_transription_status(transcription_id)
        #print("transcription_status", transcription_status, transcription_status != "COMPLETED" )
        perf[transcription_status]=perf[transcription_status]+1
        print(" transcription_status: " + transcription_status + " " + str(perf[transcription_status]), end='\r' )
    transcription_lat=get_transription_lat(transcription_id)
    
    if(transcription_lat == ""):
        logging.error("Error. Transcription lat not found")
        return
    logging.info("Peformance status in seconds:" + str(perf))
    output_file_path = wav_path+".txt"
    f = open(output_file_path, "w")
    logging.info(f"Wring result to {output_file_path}")
    f.write(transcription_lat)
    f.close()
        

def print_wav_files_in_directory(directory):
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
        print_wav_files_in_directory(directory)