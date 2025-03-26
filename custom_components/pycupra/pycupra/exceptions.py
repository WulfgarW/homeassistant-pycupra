class SeatConfigException(Exception):
    """Raised when Seat Connect API client is configured incorrectly"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatConfigException, self).__init__(status)
        self.status = status

class SeatAuthenticationException(Exception):
    """Raised when credentials are invalid during authentication"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatAuthenticationException, self).__init__(status)
        self.status = status

class SeatAccountLockedException(Exception):
    """Raised when account is locked from too many login attempts"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatAccountLockedException, self).__init__(status)
        self.status = status

class SeatTokenExpiredException(Exception):
    """Raised when server reports that the access token has expired"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatTokenExpiredException, self).__init__(status)
        self.status = status

class SeatException(Exception):
    """Raised when an unknown error occurs during API interaction"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatException, self).__init__(status)
        self.status = status

class SeatThrottledException(Exception):
    """Raised when the API throttles the connection"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatThrottledException, self).__init__(status)
        self.status = status

class SeatEULAException(Exception):
    """Raised when EULA must be accepted before login"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatEULAException, self).__init__(status)
        self.status = status

class SeatLoginFailedException(Exception):
    """Raised when login fails for an unknown reason"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatLoginFailedException, self).__init__(status)
        self.status = status

class SeatInvalidRequestException(Exception):
    """Raised when an unsupported request is made"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatInvalidRequestException, self).__init__(status)
        self.status = status

class SeatRequestInProgressException(Exception):
    """Raised when a request fails because another request is already in progress"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatRequestInProgressException, self).__init__(status)
        self.status = status

class SeatServiceUnavailable(Exception):
    """Raised when a API is unavailable"""

    def __init__(self, status):
        """Initialize exception"""
        super(SeatServiceUnavailable, self).__init__(status)
        self.status = status
