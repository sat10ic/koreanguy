from logging.handlers import TimedRotatingFileHandler

from manas_os.ops_logging import rotating_file_handler


def test_rotating_file_handler_keeps_fourteen_dated_backups(tmp_path):
    handler = rotating_file_handler("pipeline", log_dir=tmp_path)
    try:
        assert isinstance(handler, TimedRotatingFileHandler)
        assert handler.backupCount == 14
        assert handler.suffix == "%Y-%m-%d"
        assert handler.baseFilename == str(tmp_path / "pipeline.log")
    finally:
        handler.close()
