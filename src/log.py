import logging
import coloredlogs
from config import DEBUG

def init_log(filename):
    """
    :param filename
    :return logger
    """
    FIELD_STYLES = dict(
        asctime=dict(color='green'),
        hostname=dict(color='magenta'),
        levelname=dict(color='green'),
        filename=dict(color='magenta'),
        name=dict(color='blue'),
        threadName=dict(color='green')
    )

    LEVEL_STYLES = dict(
        debug=dict(color='green'),
        info=dict(color='cyan'),
        warning=dict(color='yellow'),
        error=dict(color='red'),
        critical=dict(color='red')
    )
    # formattler = '%(asctime)s %(pathname)-8s:%(lineno)d %(levelname)-8s %(message)s'
    # formattler = '%(levelname)-8s %(message)s'
    formattler = '[%(levelname)-7s] [%(filename)-8s:%(lineno)-3d] %(message)s'
    fmt = logging.Formatter(formattler)
    logger = logging.getLogger()
    if DEBUG:
        level = logging.DEBUG
    else:
        level = logging.INFO
    coloredlogs.install(
        level=level,
        fmt=formattler,
        level_styles=LEVEL_STYLES,
        field_styles=FIELD_STYLES)
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    try:
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("pdfplumber").setLevel(logging.DEBUG)
        logging.getLogger("bibtexparser").setLevel(logging.WARNING)
    except Exception as e:
        pass
    return logger


