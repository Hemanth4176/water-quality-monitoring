"""
Part 2 - Data Preprocessing
Simple demo functions for the lab assignment.
"""
import csv

def read_csv(path):
    """Return list of rows (dicts) from a small CSV file."""
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)

def strip_whitespace_rows(rows, keys=None):
    """Strip whitespace from string fields for given keys (or all keys if None)."""
    out = []
    for r in rows:
        nr = {}
        for k, v in r.items():
            if keys is None or k in keys:
                # Use str() just in case v is a non-string object that needs stripping
                nr[k] = v.strip() if isinstance(v, str) else v
            else:
                nr[k] = v
        out.append(nr)
    return out

if __name__ == "__main__":
    print("preprocessing module: contains read_csv and strip_whitespace_rows")
