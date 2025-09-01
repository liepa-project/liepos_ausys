import argparse
import io
import urllib.request
# import urllib.parse
import json
# import subprocess
import uuid

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_headers(a_server_auth) -> dict:
    if a_server_auth == None:
        return {}
    return {'Authorization': f'Basic {a_server_auth}'}

def main(a_server_url:str, a_file:io.BufferedReader, a_server_auth:str, a_whisper_model:str):
    headers_auth=get_headers(a_server_auth)
    request_guid=uuid.uuid4()
    # Upload the file and get the file path
    url = f"{a_server_url}/upload?upload_id={request_guid}"
    file_path_to_upload = a_file

    # We'll use a multipart/form-data request to simulate the curl -F
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    crlf = b'\r\n'
    data = []
    data.append(b'--' + boundary.encode())
    data.append(b'Content-Disposition: form-data; name="files"; filename="zinios.wav"')
    data.append(b'Content-Type: audio/mpeg')
    data.append(b'')

    with a_file as f:
        data.append(f.read())
    data.append(b'--' + boundary.encode() + b'--')
    data.append(b'')
    body = crlf.join(data)

    headers_upload = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Content-Length': str(len(body))
    }
    headers={**headers_upload, **headers_auth}
    print("url", url)

    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        file_path_output = response.read().decode('utf-8')
        file_path = json.loads(file_path_output)[0]

    # Prepare the data for the API call
    data_payload = {
        "data": [
            {"path": file_path, "meta": {"_type": "gradio.FileData"}},
            a_whisper_model,
            False
        ]
    }

    # Make the first API call to get the event_id
    predict_url = f'{a_server_url}/call/predict'
    data_bytes = json.dumps(data_payload).encode('utf-8')

    headers_json = {
        'Content-Type': 'application/json'
    }
    headers={**headers_json, **headers_auth}

    req = urllib.request.Request(predict_url, data=data_bytes, headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        event_id_json = json.loads(response.read().decode('utf-8'))
        event_id = event_id_json.get('event_id')

    # Poll the API for the result using the event_id
    result_url = f'{a_server_url}/call/predict/{event_id}'
    req = urllib.request.Request(result_url, headers=headers)
    with urllib.request.urlopen(req) as response:
        result_output = response.read().decode('utf-8')

    # Find the line containing "data:" and extract the JSON
    for line in result_output.splitlines():
        if line.startswith('data: '):
            result_json_str = line.replace('data: ', '')
            result_json = json.loads(result_json_str)
            # Print the first element of the list
            print(result_json[0])
            break

if __name__ == "__main__":

        # 1. Create a parser object
    parser = argparse.ArgumentParser(description="Process audio files using a Whisper model API.")

    # 2. Add arguments
    # Use 'dest' to give the variable a more readable name
    parser.add_argument("--server_url", "-s", dest="server_url_gradio_api",
                        required=True,
                        help="The URL for the Gradio API server.")
    
    parser.add_argument("--auth", "-a", dest="server_auth",
                        required=True,
                        help="Base64 encoded server authentication token.")

    parser.add_argument("--file_path", "-f", dest="file_path",
                        type=argparse.FileType('rb'),
                        default="./wav/zinios.wav",
                        help="The path to the audio file to process.")

    parser.add_argument("--model", dest="whisper_model",
                        default="whisper-medium-l2c_e4",
                        help="The name of the Whisper model to use.")



    # 3. Parse the arguments
    args = parser.parse_args()

    # Now you can access the variables using the 'args' object
    print(f"Server URL: {args.server_url_gradio_api}")
    print(f"File Path: {args.file_path}")
    print(f"Whisper Model: {args.whisper_model}")
    print(f"Server Auth: {args.server_auth}")

    main(args.server_url_gradio_api, args.file_path, args.server_auth, args.whisper_model)
