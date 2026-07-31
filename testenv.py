from pathlib import Path
import os

env_path = Path(__file__).parent / ".env"

print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

if env_path.exists():
    print(f"\nContents of .env:")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key = line.split("=")[0]
                print(f"  Found key: {key}")
else:
    print("ERROR: .env file not found at that path")