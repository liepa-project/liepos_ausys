#!/usr/bin/env python
import argparse

from dataclasses import dataclass
from typing import Dict, Optional

import os
import fnmatch
import time
import uuid
import urllib.request
import json
import re

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
    hf_url:str = ""
    hf_model:str = ""
    auth:Optional[str] = None
    ext_eaf:Optional[bool] = None
    req_email:Optional[str] = None
    req_model:str = "ben"



def send_file_to_server(file_path_to_upload:str, ctx:ProcessingCtx) -> str:
    """ Send wav file to server """
    logging.debug("------------------- send_file_to_server -------------------")
    request_guid=uuid.uuid4()
    # Upload the file and get the file path
    url = f"{ctx.hf_url}/upload?upload_id={request_guid}"

    # We'll use a multipart/form-data request to simulate the curl -F
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    crlf = b'\r\n'
    data = []
    data.append(b'--' + boundary.encode())
    data.append(b'Content-Disposition: form-data; name="files"; filename="zinios.mp3"')
    data.append(b'Content-Type: audio/mpeg')
    data.append(b'')
    with open(file_path_to_upload, 'rb') as f:
        data.append(f.read())
    data.append(b'--' + boundary.encode() + b'--')
    data.append(b'')
    body = crlf.join(data)

    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body))
    }

    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    remote_file_path=None
    with urllib.request.urlopen(req) as response:
        file_path_output = response.read().decode('utf-8')
        remote_file_path = json.loads(file_path_output)[0]
        logging.debug("[send_file_to_server] remote_file_path: %s", remote_file_path)
    
    if(remote_file_path==None):
        raise Exception("Error: Server path not found")

    # Prepare the data for the API call
    data_payload = {
        "data": [
            {"path": remote_file_path, "meta": {"_type": "gradio.FileData"}},
            ctx.hf_model,
            True
        ]
    }

    predict_url = f"{ctx.hf_url}/call/predict"
    data_bytes = json.dumps(data_payload).encode('utf-8')

    headers = {
        'Content-Type': 'application/json'
    }

    req = urllib.request.Request(predict_url, data=data_bytes, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        event_id_json = json.loads(response.read().decode('utf-8'))
        logging.debug("[send_file_to_server]event_id_json %s", event_id_json)
        event_id = event_id_json.get('event_id')

    return event_id

    
    # with open(file_path, 'rb') as file:
    #     files = {'file': (file_path, file, 'multipart/form-data')}
    #     data = {'recognizer': ctx.req_model, "email":ctx.req_email}
    #     data = {k: v for k, v in data.items() if v is not None}
    #     send_url=f"{ctx.ausis_url}/transcriber/upload"
    #     # logging.debug(f"Sending request to: {send_url} ")
    #     response = requests.post(send_url, files=files, data=data, headers=get_headers(ctx))
    #     transcription_id=""
    #     if(response.ok):
    #         response_json = response.json()
    #         #print(response_json)
    #         transcription_id=response_json["id"]
    #         logging.info(f'transcription id:{transcription_id}')
    #     else:
    #         logging.error(f"Error: {response.status_code}, {response.text}")
    #         raise Exception("Error from server!")
    #     return transcription_id

def get_transription_lat(result_name:str, transcription_id:str, ctx:ProcessingCtx) -> str:
    """ Retrieve lat file content """
    logging.debug("------------------- get_transription_lat -------------------")

    result_url = f"{ctx.hf_url}/call/predict/{transcription_id}"
    req = urllib.request.Request(result_url)
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
            break
    return lat_text


def save_transription_result( wav_path:str, result_name:str, result_ext:str,  transcription_id:str, ctx:ProcessingCtx) -> str:
    """save requested transcription format"""
    transcription_lat=get_transription_lat(result_name, transcription_id, ctx)
    if(transcription_lat == ""):
        logging.error(f"Error. Transcription '{result_name}' not found")
        return "---"
    output_file_path = re.sub('wav$', result_ext, wav_path)
    # f = open(output_file_path, "w")
    with open(output_file_path, "w", encoding="utf-8") as f:
        logging.info(f"Wring result to {output_file_path}")
        f.write(transcription_lat)

def transcription(wav_path:str, ctx:ProcessingCtx):
    transcription_id=send_file_to_server(wav_path, ctx)
    if(transcription_id == ""):
        logging.error("Error. Transcription ID not found")
        return
    # logging.debug("liepa_ausys_processing_timeout_sec: %s",liepa_ausys_processing_timeout_sec)
    # while_timeout = time.time() + liepa_ausys_processing_timeout_sec
    # transcription_status=""
    # while transcription_status != "COMPLETED":
    save_transription_result(wav_path=wav_path, result_name="lat.restored.txt", result_ext='lat', transcription_id=transcription_id, ctx=ctx)


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
    if env_dict["hf_url"] == "":
        logging.info("hf_url is not set in liepa_ausys.env")
        param_error=True
    if env_dict["hf_model"] == "":
        logging.info("hf_model is not set in liepa_ausys.env")
        param_error=True
    if param_error:
        logging.error("Error occured. Exiting...")
    else:
        ctx=ProcessingCtx()
        ctx.directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")
        ctx.hf_url=env_dict["hf_url"]
        ctx.hf_model=env_dict["hf_model"]
        ctx.req_email=env_dict["liepa_ausys_email"]

        # liepa_ausys_processing_timeout_sec=int(env_dict.get("liepa_ausys_processing_timeout_sec",liepa_ausys_processing_timeout_sec))
        logging.info(f"hf_url: {ctx.hf_url}")
        logging.info(f"hf_model: {ctx.hf_model}")
        ctx.ext_eaf=args.ext_eaf

        ctx.auth=env_dict["liepa_ausys_auth"]
        # if auth != None:
        #     ausis_headers = {'Authorization': f'Basic {auth}'}
        transcribe_wav_files_in_directory(ctx)
