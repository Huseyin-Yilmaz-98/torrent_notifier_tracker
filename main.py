from Tracker import Tracker
import os

if __name__ == "__main__":
    if "info.json" not in os.listdir():
        print("info.json not found in the working directory, ending the program!")
        exit()

    Tracker().start()
