# pydd - pydupedeleter

pydd is a Python script that scans specified directories for movie release folders, groups them by a canonical key (using the IMDB ID from .nfo files if available, otherwise by title and year extracted from the folder name), and then calculates a score for each folder based on user‐defined regex patterns. In each duplicate group the folder with the highest score is kept while the others are flagged as duplicates (or deleted, if enabled).

## How It Works

### 1. Grouping Directories
- **IMDB Extraction:**  
  The script looks for a `.nfo` file in each folder and attempts to extract an IMDB ID (e.g. `tt0044706`).  
- **Canonical Name:**  
  If no IMDB ID is found, the script extracts a candidate title and year from the folder name (using a regex) and forms a canonical name (e.g. `"die coal valley saga 2014"`).
- **Grouping:**  
  Folders are initially grouped using the IMDB ID (if available). In case the IMDB-based group contains folders with differing canonical names (indicating different releases), the group is split using the canonical name.

### 2. Score Function
The score function calculates a numeric value for each folder based on a list of regex patterns provided in the configuration file. It works as follows:
- **Pattern Matching:**  
  For each regex pattern, the function checks if the folder name matches the pattern.
- **Score Accumulation:**  
  If a match is found, the score associated with that pattern is added to the folder’s total score.
- **Example:**  
  - A pattern like `BluRay*x26[45]*` with a score of `900` will add 900 points if the folder name matches this regex.  
  - A pattern like `.*UNRATED.*` with a score of `50` adds 50 points if the folder name contains "UNRATED".

The folder with the highest score in a group is chosen as the “best” version, and the others are marked as duplicates.

### 3. Duplicate Resolution
After grouping and scoring:
- **Duplicate Folders:**  
  In groups with more than one folder, only the folder with the highest score is kept.
- **Deletion Option:**  
  With the `--delete` flag (and optionally `--dry-run` for simulation), the script can delete the duplicate folders.