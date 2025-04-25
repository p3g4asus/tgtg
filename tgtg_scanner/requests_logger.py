import logging
import sys
import requests
import textwrap


class HttpFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', validate=True, formatter: logging.Formatter = None):
        super().__init__(fmt, datefmt, style, validate)
        self.additional_formatter = formatter

    def _formatHeaders(self, d):
        return '\n'.join(f'{k}: {v}' for k, v in d.items())

    def formatMessage(self, record):
        result = super().formatMessage(record)
        if record.name == 'httplogger':
            result += textwrap.dedent('''
                ---------------- request ----------------
                {req.method} {req.url}
                {reqhdrs}

                {req.body}
                ---------------- response ----------------
                {res.status_code} {res.reason} {res.url}
                {reshdrs}

                {res.text}
            ''').format(
                req=record.req,
                res=record.res,
                reqhdrs=self._formatHeaders(record.req.headers),
                reshdrs=self._formatHeaders(record.res.headers),
            )
        elif self.additional_formatter:
            result = self.additional_formatter.formatMessage(record)
        return result


def get_requests_logger(level: int = logging.DEBUG, handler2: logging.Handler = None):
    formatter = HttpFormatter('{asctime} {levelname} {name} {message}', style='{', formatter=handler2.formatter if handler2 else None)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger('httplogger')
    if handler2:
        handler2.setFormatter(formatter)
        logger.handlers = [handler, handler2]
    else:
        logger.handlers = [handler]
    logger.setLevel(level)
    return logger


_REQUESTS_LOGGER = None


def init_requests_logger(level: int = logging.DEBUG, *handlers):
    """
    Initialize the requests logger with the specified logging level.
    """
    global _REQUESTS_LOGGER
    if _REQUESTS_LOGGER is None:
        _REQUESTS_LOGGER = get_requests_logger(level, *handlers)
    else:
        _REQUESTS_LOGGER.setLevel(level)


def logRoundtrip(response, *args, **kwargs):
    extra = {'req': response.request, 'res': response}
    _REQUESTS_LOGGER.debug('HTTP roundtrip', extra=extra)


def hook_session(session):
    """
    Add the roundtrip logging hook to a requests session.
    """
    if not isinstance(session, requests.Session):
        raise TypeError('session must be a requests.Session instance')
    if _REQUESTS_LOGGER is not None:
        session.hooks['response'].append(logRoundtrip)
    return session

