"""Password strength rules.

The policy follows NIST SP 800-63B-4, which moved away from character-composition rules
("one capital, one digit, one symbol") because they push people towards predictable
patterns without making passwords harder to guess. Instead it asks for:

* a generous minimum length (15 characters when the password is the only factor);
* support for long passphrases, including spaces and any Unicode character;
* rejection of passwords that are known to be common or that contain obvious context
  such as the person's own email name or the name of the service.

Length is counted in Unicode characters (code points), not bytes, so a password typed in
any script is treated fairly.
"""

import unicodedata
from collections.abc import Iterable

# A starter list of very common passwords, all lower case. It is deliberately small. A
# production deployment should also check candidates against a large corpus of breached
# passwords, for example the "Pwned Passwords" range API, which answers without ever
# receiving the password itself.
COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "123456",
        "12345678",
        "123456789",
        "qwerty",
        "iloveyou",
        "admin",
        "letmein",
        "welcome",
        "abc123",
        "passwordpassword",
        "password1234567",
        "password12345678",
        "123456789012345",
        "1234567890123456",
        "12345678901234567890",
        "qwertyuiopasdfgh",
        "qwertyuiop123456",
        "qwertyuiopasdfghjkl",
        "iloveyouiloveyou",
        "iloveyou1234567",
        "letmeinletmein",
        "welcome12345678",
        "administrator123",
        "adminadminadmin",
        "abcdefghijklmnop",
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789abcdef",
        "1q2w3e4r5t6y7u8i",
        "zaq12wsxcde34rfv",
        "asdfghjklasdfghjkl",
        "trustno1trustno1",
        "footballfootball",
        "monkeymonkeymonkey",
        "dragondragondragon",
        "bloodlink123456789",
        "bloodlinkbloodlink",
    }
)

# A password built from fewer distinct characters than this (for example a short pattern
# repeated until it is long enough) is rejected as trivially guessable.
MIN_DISTINCT_CHARACTERS = 5

# Context words shorter than this are ignored, because matching them would reject
# perfectly good passwords by coincidence.
MIN_CONTEXT_TERM_LENGTH = 4


class PasswordPolicyError(ValueError):
    """Raised when a password does not meet the policy. The message is safe to show users."""


def validate_password(
    password: str,
    *,
    min_length: int,
    max_length: int,
    context_terms: Iterable[str] = (),
) -> None:
    """Check a candidate password against the policy.

    Args:
        password: The candidate password, exactly as typed.
        min_length: Shortest acceptable length in Unicode characters.
        max_length: Longest acceptable length in Unicode characters.
        context_terms: Words the password must not contain, such as the name part of the
            person's email address or the service name. Terms shorter than
            ``MIN_CONTEXT_TERM_LENGTH`` are ignored.

    Raises:
        PasswordPolicyError: With a user-facing explanation of the first rule broken.
    """
    length = len(password)
    if length < min_length:
        raise PasswordPolicyError(f"Password must be at least {min_length} characters long.")
    if length > max_length:
        raise PasswordPolicyError(f"Password must be at most {max_length} characters long.")

    # Compare in a normalised, case-insensitive form so "PASSWORDpassword" is caught too.
    comparable = unicodedata.normalize("NFKC", password).casefold()

    if comparable in COMMON_PASSWORDS:
        raise PasswordPolicyError(
            "This password is too common. Choose a longer, less predictable one."
        )

    if len(set(comparable)) < MIN_DISTINCT_CHARACTERS:
        raise PasswordPolicyError("Choose a password that uses a greater variety of characters.")

    for term in context_terms:
        cleaned = term.strip().casefold()
        if len(cleaned) >= MIN_CONTEXT_TERM_LENGTH and cleaned in comparable:
            raise PasswordPolicyError(
                "Password must not contain your email name or the name of this service."
            )
