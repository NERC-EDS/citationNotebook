import csv
import json

def convertCSVtoJSON(csv_file_path, json_file_path):
    
    data = {}

    # Read the CSV file and group the data by `dataset_publisher_processed`
    with open(csv_file_path, "r", encoding="utf-8") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            publisher = row["data_Publisher"]
            if publisher not in data:
                data[publisher] = []
            data[publisher].append(row)

    # Write the data to a JSON file
    with open(json_file_path, "w", encoding="utf-8") as jsonfile:
        json.dump(data, jsonfile, indent=4)
