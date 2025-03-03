
import sys
import traceback
import time
import os

# Define the main function to run the actual application
def run_main():
    try:
        # Import and run the main module
        import Map2
        # If Map2 is a module, we might need to call its main function
        if hasattr(Map2, 'main'):
            Map2.main()
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        
        # Also write to a log file
        log_file = os.path.join(os.path.dirname(sys.executable), 'error_log.txt')
        try:
            with open(log_file, 'w') as f:
                f.write(f"ERROR: {type(e).__name__}: {e}\n")
                f.write("\nFull traceback:\n")
                traceback.print_exc(file=f)
        except Exception as log_err:
            print(f"Failed to write to log file: {log_err}")
            
        print("\nPress Enter to exit...")
        input()  # Wait for user input before closing

if __name__ == "__main__":
    print("Starting application in debug mode...")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current sys.path:")
    for i, path in enumerate(sys.path):
        print(f"  [{i}] {path}")
    
    try:
        print("\nAttempting to import SeisWare...")
        import SeisWare
        print(f"SeisWare imported successfully from: {getattr(SeisWare, '__file__', 'Unknown')}")
        
        # Try importing the specific SDK module
        print("\nAttempting to import SeisWare.seisware_sdk_312...")
        try:
            from SeisWare import seisware_sdk_312
            print("Successfully imported seisware_sdk_312")
        except ImportError as e:
            print(f"Failed to import seisware_sdk_312: {e}")
            
            # Check if the file exists
            if hasattr(SeisWare, '__file__'):
                seisware_dir = os.path.dirname(SeisWare.__file__)
                sdk_path = os.path.join(seisware_dir, 'seisware_sdk_312.py')
                print(f"Checking if SDK file exists at: {sdk_path}")
                if os.path.exists(sdk_path):
                    print(f"  File exists!")
                    
                    # List the contents of the SeisWare directory
                    print(f"Contents of {seisware_dir}:")
                    try:
                        for file in os.listdir(seisware_dir):
                            print(f"  - {file}")
                    except Exception as e:
                        print(f"  Error listing directory: {e}")
                else:
                    print(f"  File does not exist!")
        
    except ImportError as e:
        print(f"Failed to import SeisWare: {e}")
    except Exception as e:
        print(f"Error when importing SeisWare: {type(e).__name__}: {e}")
    
    # Run the main application
    print("\nLaunching main application...")
    run_main()
