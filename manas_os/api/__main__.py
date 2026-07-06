"""Run the API:  python -m manas_os.api   → uvicorn on :8000."""
import uvicorn


def main() -> None:
    uvicorn.run("manas_os.api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
