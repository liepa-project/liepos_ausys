#!/usr/bin/env python
import argparse

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import os
import fnmatch
import time
import uuid
import urllib.request
import json
import re
from pathlib import Path


import logging
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

@dataclass
class ProcessingCtx():
    directory: str = ""
    ausis_url:str = ""
    whisper_url:str = ""
    whisper_model:str = ""
    auth:Optional[str] = None
    ext_eaf:Optional[bool] = None
    req_model:str = "ben"

def get_headers(ctx:ProcessingCtx):
    if ctx.auth != None:
        return {'Authorization': f'Basic {ctx.auth}', 
                'Content-Type': 'application/json'}
    return {}

def send_file_to_server(file_path_to_upload:str, ctx:ProcessingCtx) -> str:
    """ Send wav file to server """
    logging.debug("------------------- send_file_to_server -------------------")
    file_name=Path(file_path_to_upload).name
    logging.debug("[send_file_to_server] file_path_to_upload: %s", file_name)
    
    request_guid=uuid.uuid4()
    # Upload the file and get the file path
    url = f"{ctx.whisper_url}/upload?upload_id={request_guid}"

    # We'll use a multipart/form-data request to simulate the curl -F
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    crlf = b'\r\n'
    data = []
    data.append(b'--' + boundary.encode())
    # data.append(b'Content-Disposition: form-data; name="files"; filename="zinios.mp3"')
    data.append(f'Content-Disposition: form-data; name="files"; filename="{file_name}"'.encode())
    

    data.append(b'Content-Type: audio/mpeg')
    data.append(b'')
    with open(file_path_to_upload, 'rb') as f:
        data.append(f.read())
    data.append(b'--' + boundary.encode() + b'--')
    data.append(b'')
    body = crlf.join(data)

    headers_upload = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body))
    }
    headers_main=get_headers(ctx)
    headers={**headers_main, **headers_upload}



    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    remote_file_path=None
    with urllib.request.urlopen(req) as response:
        file_path_output = response.read().decode('utf-8')
        remote_file_path = json.loads(file_path_output)[0]
        logging.debug("[send_file_to_server] remote_file_path: %s", remote_file_path)
    
    if(remote_file_path==None):
        raise Exception("Error: Server path not found")
    return remote_file_path

def predict_transcription(remote_file_path:str):
    # Prepare the data for the API call
    data_payload = {
        "data": [
            {"path": remote_file_path, "meta": {"_type": "gradio.FileData"}},
            ctx.whisper_model,
            False
        ]
    }

    predict_url = f"{ctx.whisper_url}/call/predict"
    data_bytes = json.dumps(data_payload).encode('utf-8')

    headers=get_headers(ctx)

    req = urllib.request.Request(predict_url, data=data_bytes, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        event_id_json = json.loads(response.read().decode('utf-8'))
        logging.debug("[predict_transcription]event_id_json %s", event_id_json)
        transcription_id = event_id_json.get('event_id')
        return transcription_id
    


def get_transription_lat(result_name:str, transcription_id:str, ctx:ProcessingCtx) -> Tuple[str,dict]:
    """ Retrieve lat file content """
    logging.debug("------------------- get_transription_lat -------------------")

    result_url = f"{ctx.whisper_url}/call/predict/{transcription_id}"
    headers=get_headers(ctx)
    req = urllib.request.Request(result_url, headers=headers)
    result_output = "---"
    with urllib.request.urlopen(req) as response:
        result_output = response.read().decode('utf-8')
    logging.debug("[get_transription_lat]predict result_output:\n %s \n---", result_output)
    lat_text="UNKOWN"
    # Find the line containing "data:" and extract the JSON
    for line in result_output.splitlines():
        result_json_str = line.replace('data: ', '')
        if line.startswith('data: ' ) and line != "data: null":
            logging.debug("[get_transription_lat]result_json_str %s", result_json_str)
            result_json = json.loads(result_json_str)
            logging.debug("[get_transription_lat]result_json %s", result_json)
            # Print the first element of the list
            logging.debug("[get_transription_lat]extracted result_json[0] %s", result_json[0])
            # lat_text=result_json[0]
            lat_text=result_json[0]
            data_list=result_json[1]["data"]
            logging.debug("[get_transription_lat]extracted result_json[1].data %s", data_list)
            procesing_time_breakdown={item[0]: item[1] for item in data_list}
            logging.debug("[get_transription_lat]procesing_time_breakdown %s", procesing_time_breakdown)
            break
    return lat_text, procesing_time_breakdown


def save_transription_result( wav_path:str, result_name:str, result_ext:str,  transcription_id:str, ctx:ProcessingCtx) -> Tuple[str,dict]:
    """save requested transcription format"""
    transcription_lat, procesing_time_breakdown=get_transription_lat(result_name, transcription_id, ctx)
    if(transcription_lat == ""):
        logging.error(f"Error. Transcription '{result_name}' not found")
        return "---", {}
    output_file_path = re.sub('wav$', result_ext, wav_path)
    output_file_path = re.sub('mp3$', result_ext, output_file_path)
    # f = open(output_file_path, "w")
    with open(output_file_path, "w", encoding="utf-8") as f:
        logging.info(f"Wring result to {output_file_path}")
        f.write(transcription_lat)
    return output_file_path, procesing_time_breakdown

def transcription(wav_path:str, ctx:ProcessingCtx):
    """
    Transcription
    """
    wav_length_in_sec=get_audio_duration(wav_path)
    logging.info(f"Sound files: {wav_path}. Length: {wav_length_in_sec:.2f} s")
    if(wav_length_in_sec == 0):
        logging.error("Error. File length is 0")
        return
    processing_time_per_status={}
    start_time = time.time()
    remote_file=send_file_to_server(wav_path, ctx)
    
    if(remote_file == ""):
        logging.error("Error. Remote file not found")
        return
    transcription_id = predict_transcription(remote_file)
    # logging.debug("liepa_ausys_processing_timeout_sec: %s",liepa_ausys_processing_timeout_sec)
    # while_timeout = time.time() + liepa_ausys_processing_timeout_sec
    # transcription_status=""
    # while transcription_status != "COMPLETED":
    output_file_path, procesing_time_breakdown = save_transription_result(wav_path=wav_path, result_name="lat.restored.txt", result_ext='lat', transcription_id=transcription_id, ctx=ctx)
    total_processing_time_in_sec = time.time() - start_time
    logging.info(f"\tClient waiting time(sec): {total_processing_time_in_sec:.2f} (Ratio {total_processing_time_in_sec/wav_length_in_sec:.2f})")
    formatted_strings = list(map(lambda item: f"{item[0].title()}: {item[1]:.2f}", procesing_time_breakdown.items()))
    logging.info(f"\tServer processing time:{formatted_strings}")


def transcribe_wav_files_in_directory(ctx:ProcessingCtx):
    """ Iterate through dir to get transcriptions """
    logging.debug("------------------- transcribe_wav_files_in_directory -------------------")
    try:
        p = Path(ctx.directory)
        for entry in os.listdir(p):
            full_path = os.path.join(p, entry)
            if os.path.isfile(full_path) and ( fnmatch.fnmatch(entry, "*.wav")): #fnmatch.fnmatch(entry, "*.mp3") or
                logging.info("Processing: %s ", full_path)
                transcription(full_path, ctx)
            else:
                logging.debug("Skiping: %s", full_path)
    except FileNotFoundError:
        logging.error(f"Error: Directory '{ctx.directory}' not found.")
    except PermissionError:
        logging.error(f"Error: Permission denied for accessing '{ctx.directory}'.")

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
    argparser = argparse.ArgumentParser(description='Hf whisper space  is client')
    # Optional positional argument
    argparser.add_argument('-u', '--url', type=str, nargs='?', 
                        help='An optional url where server is')

    argparser.add_argument('-e', '--env', type=str, nargs='?', default="liepa_ausys.env",
                        help='An optional file path of env variables')
    argparser.add_argument('--ext_eaf', action=argparse.BooleanOptionalAction, help='An optional param if EAF format should be extracted')

    args = argparser.parse_args()
    
    param_error=False
    env_dict=parse_env_file(args.env)
    if env_dict["liepa_ausys_wav_path"] == "":
        logging.info("liepa_ausys_wav_path is not set in liepa_ausys.env")
        param_error=True
    if env_dict["whisper_url"] == "":
        logging.info("hf_url is not set in liepa_ausys.env")
        param_error=True
    # if env_dict["whisper_model"] == "":
    #     logging.info("hf_model is not set in liepa_ausys.env")
    #     param_error=True
    if param_error:
        logging.error("Error occured. Exiting...")
    else:
        ctx=ProcessingCtx()
        ctx.directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")
        ctx.directory = env_dict["liepa_ausys_wav_path"].replace("*.mp3","")
        ctx.whisper_url=env_dict["whisper_url"]
        ctx.whisper_model=env_dict["whisper_model"] if "whisper_model" in env_dict else "whisper-medium-l2c_e4"

        # liepa_ausys_processing_timeout_sec=int(env_dict.get("liepa_ausys_processing_timeout_sec",liepa_ausys_processing_timeout_sec))
        logging.info(f"whisper_url: {ctx.whisper_url}")
        logging.info(f"whisper_model: {ctx.whisper_model}")
        logging.info(f"Directory: {ctx.directory}")
        ctx.ext_eaf=args.ext_eaf

        ctx.auth=env_dict["liepa_ausys_auth"]
        # if auth != None:
        #     ausis_headers = {'Authorization': f'Basic {auth}'}
        transcribe_wav_files_in_directory(ctx)
