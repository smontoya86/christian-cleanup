import sys
import os

print(f"--- Python Environment Diagnostics ---")
print(f"Running with sys.executable: {sys.executable}")
print(f"Python version: {sys.version.splitlines()[0]}")
print(f"Current working directory: {os.getcwd()}")

print("\nAttempting to import 'torch'...")
try:
    import torch
    print("Successfully imported torch.")
    print(f"Torch version: {torch.__version__}")
except ImportError as e:
    print(f"Failed to import torch: {e}")

print("\nsys.path details:")
for p in sys.path:
    print(f"  {p}")

print(f"\nPYTHONPATH environment variable: {os.environ.get('PYTHONPATH')}")
print(f"VIRTUAL_ENV environment variable: {os.environ.get('VIRTUAL_ENV')}")
print("--- End of Diagnostics ---")
