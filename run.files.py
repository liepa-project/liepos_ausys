#!/usr/bin/env python
import os
import fnmatch
import requests
import time
import logging
import re
import argparse
from dataclasses import dataclass
from typing import Dict





# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def parse_env_file(file_path:str):
    env_dict = {}
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
    return env_dict



liepa_ausys_processing_timeout_sec:int=86400 #1day
liepa_ausys_processing_poll_sec:int=3 #1h
# Instantiate the parser
argparser = argparse.ArgumentParser(description='Semantika Ausis is client')
# Optional positional argument
argparser.add_argument('-u', '--url', type=str, nargs='?', 
                    help='An optional url where server is')

argparser.add_argument('-e', '--env', type=str, nargs='?', default="liepa_ausys.env",
                    help='An optional file path of env variables')
argparser.add_argument('--ext_eaf', action=argparse.BooleanOptionalAction, help='An optional param if EAF format should be extracted')


@dataclass
class ProcessingCtx():
    directory: str = ""
    ausis_url:str = ""
    auth:str = None
    ext_eaf:bool = None
    req_email:str = None
    req_model:str = "ben"

def get_headers(ctx:ProcessingCtx):
    if ctx.auth != None:
        return {'Authorization': f'Basic {ctx.auth}'}
    return {}



def transcription(wav_path:str, ctx:ProcessingCtx):
    """Orchestration procedure to send file to server, ping for statuses till result could be recieved"""
    wav_length_in_sec=get_audio_duration(wav_path)
    logging.info(f"Sound files: {wav_path}. Length: {wav_length_in_sec} s")
    if(wav_length_in_sec == 0):
        logging.error("Error. File length is 0")
        return
    transcription_id=send_file_to_server(wav_path, ctx)
    if(transcription_id == ""):
        logging.error("Error. Transcription ID not found")
        return
    
    logging.debug("liepa_ausys_processing_timeout_sec: %s",liepa_ausys_processing_timeout_sec)
    while_timeout = time.time() + liepa_ausys_processing_timeout_sec
    transcription_status=""
    processing_time_per_status={}#"Diarization":0,"ResultMake":0,"ResultMake":0, "COMPLETED":0, "Transcription":0
    while transcription_status != "COMPLETED":
        time.sleep(liepa_ausys_processing_poll_sec)
        transcription_status = check_transription_status(transcription_id, ctx)
        #print("transcription_status", transcription_status, transcription_status != "COMPLETED" )
        processing_time = processing_time_per_status.get(transcription_status, 0);
        processing_time_per_status[transcription_status]=processing_time+liepa_ausys_processing_poll_sec
        if time.time() > while_timeout:
            logging.error(f"Error. Timeout it took more than {liepa_ausys_processing_timeout_sec} sec to complete the task. adjust `liepa_ausys_processing_timeout_sec` variable per your needs.")
            raise Exception("Error: Server timeout")
        print(" transcription_status: " + transcription_status + " " + str(processing_time_per_status[transcription_status]) +10*" ", end='\r' )
    total_processing_time_in_sec = sum(processing_time_per_status.values())
    logging.info(f"Processing  took seconds: {total_processing_time_in_sec} (Ratio {total_processing_time_in_sec/wav_length_in_sec}). Breakdown:{str(processing_time_per_status)}")

    save_transription_result(wav_path=wav_path, result_name="lat.restored.txt", result_ext='lat', transcription_id=transcription_id, ctx=ctx)
    if ctx.ext_eaf == True:
        save_transription_result(wav_path=wav_path, result_name="result.eaf", result_ext='eaf', transcription_id=transcription_id, ctx=ctx)


def transcribe_wav_files_in_directory(ctx:ProcessingCtx):
    """ Iterate through dir to get transcriptions """
    logging.debug("------------------- transcribe_wav_files_in_directory -------------------")
    try:
        for entry in os.listdir(ctx.directory):
            full_path = os.path.join(ctx.directory, entry)
            if os.path.isfile(full_path) and fnmatch.fnmatch(entry, "*.wav"):
                transcription(full_path, ctx)
    except FileNotFoundError:
        logging.error(f"Error: Directory '{ctx.directory}' not found.")
    except PermissionError:
        logging.error(f"Error: Permission denied for accessing '{ctx.directory}'.")

def send_file_to_server(file_path:str, ctx:ProcessingCtx) -> str:
    """ Send wav file to server """
    logging.debug("------------------- send_file_to_server -------------------")
    
    with open(file_path, 'rb') as file:
        files = {'file': (file_path, file, 'multipart/form-data')}
        data = {'recognizer': ctx.req_model, "email":ctx.req_email}
        data = {k: v for k, v in data.items() if v is not None}
        send_url=f"{ctx.ausis_url}/transcriber/upload"
        # logging.debug(f"Sending request to: {send_url} ")
        response = requests.post(send_url, files=files, data=data, headers=get_headers(ctx))
        transcription_id=""
        if(response.ok):
            response_json = response.json()
            #print(response_json)
            transcription_id=response_json["id"]
            logging.info(f'transcription id:{transcription_id}')
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
            raise Exception("Error from server!")
        return transcription_id


def check_transription_status(transcription_id:str, ctx:ProcessingCtx) -> str: 
    """ping server to get status """
    logging.debug("------------------- check_transription_status -------------------")
    status_url=f"{ctx.ausis_url}/status.service/status/{transcription_id}"
    # print(f"Sending request to: {status_url} ")
    response = requests.get(status_url,  headers=get_headers(ctx))
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
            raise Exception("Error from server!")
    else:
        logging.error(f"Error: Server response: {response.status_code}, {response.text}")
        
    return status


def save_transription_result( wav_path:str, result_name:str, result_ext:str,  transcription_id:str, ctx:ProcessingCtx) -> str:
    """save requested transcription format"""
    transcription_lat=get_transription_lat(result_name, transcription_id, ctx)
    if(transcription_lat == ""):
        logging.error(f"Error. Transcription '{result_name}' not found")
        return ""
    output_file_path = re.sub('wav$', result_ext, wav_path)
    # f = open(output_file_path, "w")
    with open(output_file_path, "w", encoding="utf-8") as f:
        logging.info(f"Wring result to {output_file_path}")
        f.write(transcription_lat)


def get_transription_lat(result_name:str, transcription_id:str, ctx:ProcessingCtx) -> str:
    """ Retrieve lat file content """
    logging.debug("------------------- get_transription_lat -------------------")
    lat_result_url=f"{ctx.ausis_url}/result.service/result/{transcription_id}/{result_name}"
    # logging.debug(f"Sending request to: {lat_result_url} ")
    response = requests.get(lat_result_url,  headers=get_headers(ctx))
    lat_text=""
    if(response.ok):
        lat_text=response.text
    else:
        logging.error(f"Server response: {response.status_code}, {response.text}")
        raise Exception("Error from server!")
    return lat_text
        

def get_audio_duration(file_path:str) -> float:
    """ calcualte Wav file lenght in seconds"""
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
    args = argparser.parse_args()
    server_ausis_url=""
    param_error=False
    env_dict=parse_env_file(args.env)
    if env_dict["liepa_ausys_wav_path"] == "":
        logging.info("liepa_ausys_wav_path is not set in liepa_ausys.env")
        param_error=True
    if env_dict["liepa_ausys_url"] == "" and args.url == None:
        logging.info("liepa_ausys_url is not set in liepa_ausys.env")
        param_error=True
    if param_error:
        logging.error("Error occured. Exiting...")
    else:
        ctx=ProcessingCtx()
        ctx.directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")
        env_ausis_url=env_dict["liepa_ausys_url"]
        ctx.req_email=env_dict["liepa_ausys_email"]

        liepa_ausys_processing_timeout_sec=int(env_dict.get("liepa_ausys_processing_timeout_sec",liepa_ausys_processing_timeout_sec))
        server_ausis_url=args.url[0] if args.url != None else env_ausis_url
        ctx.ausis_url=server_ausis_url.rstrip("/")
        logging.info(f"ausis_url: {ctx.ausis_url}")
        ctx.ext_eaf=args.ext_eaf

        ctx.auth=env_dict["liepa_ausys_auth"]
        # if auth != None:
        #     ausis_headers = {'Authorization': f'Basic {auth}'}
        transcribe_wav_files_in_directory(ctx)
