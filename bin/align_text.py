import csv
import logging
import os
import fnmatch
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

working_dir=os.getcwd()

def parse_env_file(file_path):
    env_path=os.path.join(working_dir,file_path) # Fix env file resolution
    env_dict = {}
    if not os.path.exists(env_path):
        logging.error(f"{env_path} does not exists")
        return env_dict
    with open(env_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
    return env_dict




def smith_waterman(A, B, match_score=2, mismatch_penalty=-1, gap_penalty=-1):
    m, n = len(A), len(B)
    
    # Initialize DP table and a table to store the traceback directions
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_score = 0
    max_pos = (0, 0)
    
    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if A[i - 1] == B[j - 1]:
                score = match_score
            else:
                score = mismatch_penalty
            dp[i][j] = max(
                0,
                dp[i - 1][j - 1] + score,  # Match/Mismatch
                dp[i - 1][j] + gap_penalty,  # Insertion (gap in B)
                dp[i][j - 1] + gap_penalty   # Deletion (gap in A)
            )
            if dp[i][j] > max_score:
                max_score = dp[i][j]
                max_pos = (i, j)
    
    # Traceback to get the aligned subsequences
    aligned_A, aligned_B = [], []
    i, j = max_pos
    while i > 0 and j > 0 and dp[i][j] != 0:
        if A[i - 1] == B[j - 1]:
            aligned_A.append(A[i - 1])
            aligned_B.append(B[j - 1])
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + gap_penalty:
            aligned_A.append(A[i - 1])
            aligned_B.append('-')
            i -= 1
        else:
            aligned_A.append('-')
            aligned_B.append(B[j - 1])
            j -= 1
    
    return reversed(aligned_A), reversed(aligned_B), max_score

def transpose_arrays(array1, array2):
    # Get the length of the longer array
    max_len = max(len(array1), len(array2))
    
    # Extend both arrays to be the same length by padding with empty strings
    array1_extended = array1 + [''] * (max_len - len(array1))
    array2_extended = array2 + [''] * (max_len - len(array2))
    sumNotmatched=0
    # Print both arrays side by side
    aligned_pairs = []
    for elem1, elem2 in zip(array1_extended, array2_extended):
        notMatched =  0 if elem1 == elem2 else 1
        sumNotmatched+=notMatched
        aligned_pairs.append((elem1,elem2,notMatched) )
        # print(f"{elem1:<10} {elem2:<10} {notMatched:<1}")
    # print(f"{sumNotmatched}, {round((sumNotmatched/max_len)*100,2 )}")
    wer=round((sumNotmatched/max_len)*100,2 )
    return (aligned_pairs, wer)


def pairs_to_csv(pairs, filename="aligned_pairs.csv"):
  """
  Converts a list of aligned pairs into a CSV file.

  Args:
    pairs: A list of tuples, where each tuple represents an aligned pair.
    filename: The name of the output CSV file.
  """

  with open(filename, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Originalas', 'Atpažinta', 'Neteisinga'])  # Header row
    writer.writerows(pairs)


def read_txt_to_array(file_path):
    try:
        with open(file_path, 'r') as file:
            # Read the entire file and split by newlines
            lines = [line.strip().lower() for line in file]
        return lines
    except FileNotFoundError:
        logging.error(f"Error: txt file '{file_path}' not found.")

def read_lat_to_array(file_path):
    result_arr=[]
    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                word_text:str=None
                main_number:int=None
                if len(parts) == 4:
                    first_number, start_time, end_time, text = parts[0:]
                    word_text=text
                    main_number=first_number
                if len(parts) == 5:
                    first_number, start_time, end_time, text, punkt = parts[0:]
                    word_text=text
                    main_number=first_number
                    #print(f"Start: {start_time}, End: {end_time}, Text: {text}")
                if main_number == "1":
                    if word_text != "<eps>":
                        words=word_text.strip().lower().split("_")
                        result_arr.extend(words)
    except FileNotFoundError:
        logging.error(f"Error: lat file '{file_path}' not found.")
    return result_arr
    


def align_transcribtions_in_directory(directory):
    try:
        for entry in os.listdir(directory):
            full_path = os.path.join(directory, entry)
            if os.path.isfile(full_path) and fnmatch.fnmatch(entry, "*.lat"):
                target_file_path = re.sub('lat$', 'txt', full_path)
                align_transcription_file(full_path, target_file_path)
    except FileNotFoundError:
        logging.error(f"Error: Directory '{directory}' not found.")
    except PermissionError:
        logging.error(f"Error: Permission denied for accessing '{directory}'.")

def align_transcription_file(result_file_path, target_file_path):
    target_array=read_txt_to_array(target_file_path)
    result_array=read_lat_to_array(result_file_path)
    aligned_target, aligned_result, max_score = smith_waterman(target_array, result_array)
    (aligned_pairs, wer) = transpose_arrays(list(aligned_target), list(aligned_result))
    output_file_path = re.sub('lat$', 'csv', result_file_path)
    logging.info(f"WER: {wer}; Max Alignment Score: {max_score}")
    pairs_to_csv(aligned_pairs,output_file_path)

if __name__ == "__main__":
    env_dict=parse_env_file("./liepa_ausys.env")
    #directory = "./wav"
    # print(env_dict)
    param_error=False
    if env_dict["liepa_ausys_wav_path"] == "":
        logging.info("liepa_ausys_wav_path is not set in liepa_ausys.env")
    directory = env_dict["liepa_ausys_wav_path"].replace("*.wav","")

    align_transcribtions_in_directory(os.path.join(working_dir,directory))

    # A=read_txt_to_array("wav-etalonas/L_RA_F4_IS023_01.txt")
    # B=read_lat_to_array("wav-etalonas/L_RA_F4_IS023_01_P.lat")

    # aligned_A, aligned_B, max_score = smith_waterman(A, B)
    # (aligned_pairs, wer) = transpose_arrays(list(aligned_A), list(aligned_B))
    # pairs_to_csv(aligned_pairs)
    # print("Max Alignment Score:", max_score)
    # print("Word Error Rate:", wer)
