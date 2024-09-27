import logging
import sys
from dataclasses import dataclass
import csv
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from dataclasses import dataclass

@dataclass
class WordData:
  """Represents a line of word data from the input file."""
  main: int
  from_time: float
  to_time: float
  words: str
  punkt: Optional[str] = None

@dataclass
class PartData:
    speaker_id: str
    part_num: int
    words: List[WordData]

def read_lat_to_array(file_path):
    parts_arr=[]
    part_data:PartData=None
    try:
        with open(file_path, 'r') as file:
            for line in file:
                parts = line.strip().split()
                if line.startswith('#'):
                    if(len(parts)<3):
                        logging.error(f"Line ?. Wrong part start: {line}")
                        raise Exception("Wrong part start")
                    part_data=PartData(
                        speaker_id=parts[2],
                        part_num=int(parts[1]),
                        words=[]
                    )
                    parts_arr.append(part_data)
                elif line.strip() == "":
                    part_data=None
                else:
                    if(len(parts) < 4):
                        logging.error(f"Line ?. Wrong line start: {line}")
                        raise Exception("Wrong line start")
                    word_data = WordData(
                        main=int(parts[0]),
                        from_time=float(parts[1]),
                        to_time=float(parts[2]), 
                        words=parts[3]                       
                    )
                    if(len(parts) > 4):
                        word_data.punkt=parts[4]
                    part_data.words.append(word_data)
    except FileNotFoundError:
        logging.error(f"Error: lat file '{file_path}' not found.")
    return parts_arr

def parts_to_csv(parts_arr:List[PartData], filename="aligned_pairs.csv"):
  """
  Converts a list of aligned pairs into a CSV file.

  Args:
    pairs: A list of tuples, where each tuple represents an aligned pair.
    filename: The name of the output CSV file.
  """

  with open(filename, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter='\t', lineterminator='\n')
    for part in parts_arr:
        for word in part.words:
            if(word.main != 1):
                continue
            row=[word.from_time, word.to_time, word.words]
            writer.writerow(row)


if __name__ == "__main__":
    file_path=sys.argv[1]
    logging.info(f"File to be process: {file_path}")
    parts_arr=read_lat_to_array(file_path)
    print("result_arr", parts_arr)
    parts_to_csv(parts_arr)