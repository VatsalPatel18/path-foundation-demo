import numpy as np
import argparse

def npy_to_bin(npy_filepath, bin_filepath):
    """Loads an .npy file, and saves it as a binary file (.bin).

    Args:
        npy_filepath: Path to the .npy file.
        bin_filepath: Path to save the .bin file.
    """
    try:
        data = np.load(npy_filepath)
    except FileNotFoundError:
        print(f"Error: File not found at {npy_filepath}")
        return
    except Exception as e:
        print(f"Error loading npy file: {e}")
        return

    with open(bin_filepath, "wb") as f:
        f.write(data.tobytes())
    print(f"Successfully converted '{npy_filepath}' to '{bin_filepath}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert .npy file to .bin file.")
    parser.add_argument("npy_file", help="Path to the input .npy file.")
    parser.add_argument("bin_file", help="Path to the output .bin file.")
    args = parser.parse_args()

    npy_to_bin(args.npy_file, args.bin_file)
