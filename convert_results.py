#!/usr/bin/env python3
"""
Script to convert ML prediction results to simple format
Extracts team names and scores from the detailed prediction file
"""

import glob
import re
import sys
from datetime import datetime
from pathlib import Path


def get_newest_result_file():
    """
    Find the newest file with format Resultados_YYYYMMDD.txt

    Returns:
        str: Path to the newest file, or None if no files found
    """
    pattern = "Resultados_????????.txt"
    files = glob.glob(pattern)

    if not files:
        return None

    # Sort by modification time, newest first
    files.sort(key=lambda x: Path(x).stat().st_mtime, reverse=True)
    return files[0]


def convert_results(input_file=None, output_file=None):
    """
    Convert the detailed prediction file to simple format

    Args:
        input_file (str): Path to input txt file (optional, will auto-detect newest)
        output_file (str): Path to output file (optional, will auto-generate)
    """
    # Auto-detect newest file if not specified
    if input_file is None:
        input_file = get_newest_result_file()
        if input_file is None:
            print("Error: No files found with format 'Resultados_YYYYMMDD.txt'")
            return
        print(f"Using newest file: {input_file}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Auto-generate output filename if not specified
    if output_file is None:
        # Extract date from input filename
        match = re.match(r"Resultados_(\d{8})\.txt", input_file)
        if match:
            date_part = match.group(1)
            output_file = f"Resultados_Simple_{date_part}.txt"
        else:
            output_file = "Resultados_Simple.txt"

    # Pattern to match team names and results
    # Team names can be mixed case, followed by "Resultado: X-Y"
    pattern = r"(.+?)\nResultado: (\d+-\d+)"

    matches = re.findall(pattern, content)

    if not matches:
        print("No matches found. Check the file format.")
        return

    # Process and clean the results
    simple_results = []
    for teams, score in matches:
        # Clean team names (remove extra spaces)
        teams_clean = " - ".join([team.strip() for team in teams.split(" - ")])
        simple_results.append(f"{teams_clean}: {score}")

    # Output results
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                for result in simple_results:
                    f.write(result + "\n")
            print(f"Results saved to: {output_file}")
        except Exception as e:
            print(f"Error writing to file: {e}")
            return

    # Also print to console
    print("\nSimple Format Results:")
    print("=" * 40)
    for result in simple_results:
        print(result)


def main():
    # Allow command line arguments
    input_file = None
    output_file = None

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    convert_results(input_file, output_file)


if __name__ == "__main__":
    main()
