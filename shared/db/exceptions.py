# Define common exceptions so services raise the same errors
# (e.g., RecordNotFound, IntegrityError).


class RecordNotFound(Exception):
    """Raised when a record is not found in the database."""

    pass
