import subprocess
import sys


def run_population_script():
    try:
        subprocess.Popen([sys.executable, 'connected_posts_database_population.py', '--depth', '2'])
        print("Population script started in the background.")
    except Exception as e:
        print(f"Failed to start population script: {e}")

if __name__ == "__main__":
    run_population_script()