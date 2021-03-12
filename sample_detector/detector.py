#!/usr/bin/python3
import helper
import time
import os

"""
    This is just a sample malware detector. Any detector can be used.
"""

def detect():
    while True:
        print("Searching...")
        for root, _, files in os.walk("/home/"):
            for f in files:
                path = os.path.join(root, f)
                if f.endswith(".mal"):
                    if path not in helper.detected:
                        print("One malware found at " + path)
                        helper.share_malware(path=path)
                    break
        time.sleep(5)

def main():
    print("Sample detector")
    detect()

if __name__ == "__main__":
    main()