from handlers import process_memory


if __name__ == "__main__":

    print("Backend is sending a Memory Job...\n")

    response = process_memory("session_001")

    print("\nBackend received:")

    print(response)