import subprocess
import sys

print("Starting score_service.py via wrapper...")
try:
    # Run score_service.py and capture everything
    result = subprocess.run(
        [sys.executable, 'score_service.py'], 
        capture_output=True, 
        text=True,
        encoding='utf-8',
        errors='replace' # Handle any weird chars gracefully
    )
    
    print(f"Finished. Return code: {result.returncode}")
    
    with open('debug_log_clean.txt', 'w', encoding='utf-8') as f:
        f.write("=== STDOUT ===\n")
        f.write(result.stdout)
        f.write("\n=== STDERR ===\n")
        f.write(result.stderr)
        
    print("Output written to debug_log_clean.txt")
except Exception as e:
    print(f"Wrapper failed: {e}")
