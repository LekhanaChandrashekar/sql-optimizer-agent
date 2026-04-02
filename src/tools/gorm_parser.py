
import subprocess
import json


def run_gorm_parser(file_path: str):
    result = subprocess.run(
        ["go", "run", "main.go", file_path],
        cwd="gorm-parser",
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(result.stdout)