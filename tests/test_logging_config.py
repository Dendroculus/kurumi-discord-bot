from utils.loggingConfig import setup_logging

def test_setup_logging_returns_logger():
    logger = setup_logging()
    assert logger.name == "bot"
    assert len(logger.handlers) == 2
    assert logger.propagate is False