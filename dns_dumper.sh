#!/bin/bash

# Variables
dir="zone_query"
zone_dump="zone.txt"
user_id="DOMAIN\\ID"
passwd="Enter password"

# Initialize an empty array to hold the trimmed lines
trimmed_lines=()

# Create the directory if it doesn't exist
mkdir -p "$dir"

# Read the zone.txt file line by line
while IFS= read -r line; do
  # Trim leading and trailing whitespace from each line
  trimmed_line=$(echo "$line" | xargs)
  
  # Store the trimmed line into the array
  trimmed_lines+=("$trimmed_line")
done < "$zone_dump"

# Run samba-tool command in loop
for line in "${trimmed_lines[@]}"; do
  echo "$line"

  samba-tool dns query localhost "$line" @ ALL -U"$user_id" --password="$passwd" > "$dir/$line.txt"
done