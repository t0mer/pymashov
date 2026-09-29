# pymashov

[![PyPI version](https://badge.fury.io/py/pymashov.svg)](https://badge.fury.io/py/pymashov)
[![Python Versions](https://img.shields.io/pypi/pyversions/pymashov.svg)](https://pypi.org/project/pymashov/)
[![License](https://img.shields.io/github/license/t0mer/pymashov.svg)](https://github.com/t0mer/pymashov/blob/main/LICENSE)

Unofficial async Python API wrapper for Mashov (משו"ב), the Israeli school management system used by students and parents.

> **Unofficial project.** pymashov is not affiliated with, endorsed by, or connected to Mashov or the Israeli Ministry of Education. It talks to the same web API that the Mashov web app uses, which is undocumented and can change without notice.

> **Responsible use.** Only use pymashov with your own account, or with the account of a child you are the parent or guardian of. The data it returns (grades, behavior records, timetables, messages) is personal information about minors. Keep it private and don't share it or store it anywhere public.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Logging](#logging)
- [Security Notes](#security-notes)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Author](#author)
- [Acknowledgments](#acknowledgments)
- [Changelog](#changelog)

## Features

- ✨ **Async/await support** - Built with modern Python async patterns using `httpx`
- 🔐 **Session handling** - Logs in with username, password, school code (semel) and year, then sends the CSRF token and session cookies on every authenticated request
- 📚 **Ready-made wrappers** - Grades, timetable, homework, behavior records, mail inbox conversations, and the public schools list
- 🛠️ **Low-level access** - `request()` and `public_request()` let you call any other Mashov endpoint
- 🔄 **Automatic login** - Logs in on the first authenticated call (can be turned off with `auto_login=False`)
- 🎯 **Type hints** - Method signatures are annotated; responses are returned as the raw JSON that Mashov sends
- 📝 **Logging** - Uses the standard `logging` module
- 🚀 **Easy to use** - Simple interface with async context manager support

## Installation

### From PyPI (Recommended)

```bash
pip install pymashov
```

### From Source

```bash
git clone https://github.com/t0mer/pymashov.git
cd pymashov
pip install -e .
```

### Requirements

- Python 3.8 or higher
- httpx >= 0.25, < 1.0 (installed automatically)
- A Mashov account (student or parent) and your school's code (semel)

Two-factor authentication is not supported: the library only performs the plain username and password login.

## Quick Start

```python
import asyncio
from mashov import MashovClient

async def main():
    # Create a client instance
    async with MashovClient(
        username="YOUR_ID",
        password="YOUR_PASSWORD",
        semel="SCHOOL_CODE",
        year="2026"  # Optional keyword argument, defaults to "2026"
    ) as client:
        # Login happens automatically on the first authenticated call
        
        # Get student grades
        student_id = "YOUR_STUDENT_ID"
        grades = await client.get_grades(student_id)
        print(f"Grades: {grades}")

asyncio.run(main())
```

`year` is the academic year as Mashov expects it. The default is the fixed string `"2026"`, not the current year, so pass it explicitly when the school year changes. <!-- TODO: verify that Mashov identifies a school year by its ending year (for example 2026 for 2025-2026) -->

The library does not provide a way to look up the student ID; the examples below assume you already have it. <!-- TODO: verify where users should get the student ID (for example from the login response, which the library currently discards) -->

## How It Works

1. **Login** - `login()` sends `POST /api/login` to `https://web.mashov.info` with a JSON body containing `username`, `password`, `semel` and `year`.
2. **Session** - A successful login must return an `x-csrf-token` response header and set session cookies (such as `MashovAuthToken` and `Csrf-Token`). If either is missing, `MashovLoginError` is raised. The result is stored as a `MashovSession`.
3. **Authenticated requests** - Every call made through `request()` (and all the `get_*` helpers except `get_schools()`) adds the `X-Csrf-Token` and `Cookie` headers from the session.
4. **Public requests** - `public_request()` (used by `get_schools()`) never logs in and adds no `X-Csrf-Token` header. Because all requests share one HTTP client, session cookies from an earlier login are still sent by the cookie jar.

The session is not refreshed automatically. If it expires, requests typically fail with `MashovRequestError`, or with a JSON decode error if the server redirects to an HTML page; call `await client.login()` again to start a new session.

## Usage Examples

> The helper methods return the JSON that Mashov sends, unchanged. The field names used below (`subject`, `grade`, `dueDate` and so on) are illustrative only. Print the response once to see the actual structure. <!-- TODO: verify response shapes and field names against real responses -->

### Manual Login

If you prefer to control when login happens:

```python
import asyncio
from mashov import MashovClient

async def main():
    client = MashovClient(
        username="YOUR_ID",
        password="YOUR_PASSWORD",
        semel="SCHOOL_CODE",
        auto_login=False  # Disable automatic login
    )
    
    try:
        # Manually login
        session = await client.login()
        print("Logged in successfully!")
        print(f"Academic year: {session.year}")
        
        # Now you can make API calls
        student_id = "YOUR_STUDENT_ID"
        grades = await client.get_grades(student_id)
        print(grades)
    finally:
        await client.close()

asyncio.run(main())
```

### Get Student Grades

```python
async def get_student_grades(client, student_id):
    """Fetch and display student grades."""
    grades = await client.get_grades(student_id)
    
    for grade in grades:
        print(f"Subject: {grade['subject']}")
        print(f"Grade: {grade['grade']}")
        print(f"Date: {grade['date']}")
        print("---")
    
    return grades
```

### Get Timetable

```python
async def get_weekly_schedule(client, student_id):
    """Fetch student's timetable."""
    timetable = await client.get_timetable(student_id)
    
    for day in timetable:
        print(f"Day: {day['day']}")
        for lesson in day['lessons']:
            print(f"  {lesson['time']}: {lesson['subject']} - {lesson['teacher']}")
    
    return timetable
```

### Get Homework Assignments

```python
async def get_pending_homework(client, student_id):
    """Fetch all homework assignments."""
    homework = await client.get_homework(student_id)
    
    for assignment in homework:
        print(f"Subject: {assignment['subject']}")
        print(f"Description: {assignment['description']}")
        print(f"Due Date: {assignment['dueDate']}")
        print("---")
    
    return homework
```

### Get Behavior Records

```python
async def check_behavior(client, student_id):
    """Fetch behavior/discipline records."""
    behavior = await client.get_behavior(student_id)
    
    for record in behavior:
        print(f"Date: {record['date']}")
        print(f"Type: {record['type']}")
        print(f"Description: {record['description']}")
        print("---")
    
    return behavior
```

### Get Mail Conversations

```python
async def get_recent_messages(client, count=10):
    """Fetch recent mail conversations."""
    conversations = await client.get_conversations(skip=0, take=count)
    
    for conv in conversations:
        print(f"From: {conv['sender']}")
        print(f"Subject: {conv['subject']}")
        print(f"Date: {conv['date']}")
        print("---")
    
    return conversations
```

### Get Available Schools

```python
async def list_schools(client):
    """Fetch list of available schools (public endpoint)."""
    schools = await client.get_schools()
    
    for school in schools:
        print(f"Name: {school['name']}")
        print(f"Code (Semel): {school['semel']}")
        print(f"City: {school['city']}")
        print("---")
    
    return schools
```

### Complete Example - Daily Student Report

```python
import asyncio
from mashov import MashovClient

async def generate_daily_report(username, password, semel, student_id):
    """Generate a comprehensive daily report for a student."""
    
    async with MashovClient(username, password, semel) as client:
        print("=" * 50)
        print("DAILY STUDENT REPORT")
        print("=" * 50)
        
        # Get grades
        print("\n📊 GRADES:")
        grades = await client.get_grades(student_id)
        for grade in grades[:5]:  # Show first 5 grades
            print(f"  • {grade.get('subject', 'N/A')}: {grade.get('grade', 'N/A')}")
        
        # Get the timetable
        print("\n📅 TIMETABLE:")
        timetable = await client.get_timetable(student_id)
        # Process and display timetable...
        
        # Get pending homework
        print("\n📝 PENDING HOMEWORK:")
        homework = await client.get_homework(student_id)
        for hw in homework[:5]:  # Show first 5 assignments
            print(f"  • {hw.get('subject', 'N/A')}: {hw.get('description', 'N/A')}")
            print(f"    Due: {hw.get('dueDate', 'N/A')}")
        
        # Get recent behavior records
        print("\n⭐ RECENT BEHAVIOR:")
        behavior = await client.get_behavior(student_id)
        for record in behavior[:3]:  # Show first 3 records
            print(f"  • {record.get('date', 'N/A')}: {record.get('description', 'N/A')}")
        
        # Get recent messages
        print("\n📧 RECENT MESSAGES:")
        messages = await client.get_conversations(skip=0, take=3)
        for msg in messages:
            print(f"  • From {msg.get('sender', 'N/A')}: {msg.get('subject', 'N/A')}")
        
        print("\n" + "=" * 50)

# Run the report
asyncio.run(generate_daily_report(
    username="YOUR_ID",
    password="YOUR_PASSWORD",
    semel="SCHOOL_CODE",
    student_id="YOUR_STUDENT_ID"
))
```

### Advanced: Custom API Requests

For endpoints not yet wrapped, use the low-level `request()` method:

```python
async def custom_api_call(client):
    """Make custom API calls to any Mashov endpoint."""
    
    # Authenticated request
    response = await client.request(
        "GET",
        "/api/custom/endpoint",
        params={"param1": "value1"}
    )
    data = response.json()
    
    # Public request (no authentication)
    response = await client.public_request(
        "GET",
        "/api/public/endpoint"
    )
    data = response.json()
    
    return data
```

## API Reference

### MashovClient

**Constructor Parameters:**
- `username` (str): Mashov username (usually the ID number)
- `password` (str): User password
- `semel` (str): School code
- `year` (str, optional): Academic year (default: "2026")
- `base_url` (str, optional): API base URL (default: "https://web.mashov.info")
- `timeout` (float, optional): Request timeout in seconds (default: 20.0)
- `auto_login` (bool, optional): Auto-login on first request (default: True)

`username`, `password` and `semel` can be passed positionally; the other parameters are keyword-only.

**Properties:**
- `is_logged_in` (bool): `True` once a session exists
- `session` (MashovSession): The current session; raises `MashovLoginError` if not logged in

**Methods:**

#### `async login() -> MashovSession`
Log in and obtain session credentials. Does not call any other endpoint.

#### `async ensure_logged_in() -> None`
Log in if there is no session yet. Raises `MashovLoginError` if there is no session and `auto_login=False`.

#### `async close() -> None`
Close the HTTP client session.

#### `async get_grades(student_id: str) -> Any`
Get student grades.

#### `async get_timetable(student_id: str) -> Any`
Get student's timetable.

#### `async get_homework(student_id: str) -> Any`
Get homework assignments.

#### `async get_behavior(student_id: str) -> Any`
Get behavior/discipline records.

#### `async get_conversations(*, skip: int = 0, take: int = 20) -> Any`
Get mail conversations from inbox. `skip` and `take` are keyword-only.

#### `async get_schools() -> Any`
Get list of available schools (public endpoint, no authentication required).

#### `async request(method: str, path: str, *, headers: dict | None = None, **kwargs) -> httpx.Response`
Low-level authenticated request method for custom API calls. Extra `kwargs` (for example `params` or `json`) are passed to `httpx.AsyncClient.request()`.

#### `async public_request(method: str, path: str, *, headers: dict | None = None, **kwargs) -> httpx.Response`
Low-level public request method (no authentication).

The client can also be used as an async context manager (`async with MashovClient(...) as client:`). Entering it does not log in; leaving it closes the HTTP client.

### Endpoints

| Method | HTTP | Path | Auth |
|--------|------|------|------|
| `login()` | POST | `/api/login` | - |
| `get_grades(student_id)` | GET | `/api/students/{student_id}/grades` | Yes |
| `get_timetable(student_id)` | GET | `/api/students/{student_id}/timetable` | Yes |
| `get_homework(student_id)` | GET | `/api/students/{student_id}/homework` | Yes |
| `get_behavior(student_id)` | GET | `/api/students/{student_id}/behave` | Yes |
| `get_conversations(skip=, take=)` | GET | `/api/mail/inbox/conversations?skip=&take=` | Yes |
| `get_schools()` | GET | `/api/schools` | No |

### MashovSession

Returned by `login()` and available as `client.session` (a frozen dataclass):

- `csrf_header_token` (str): Value of the `x-csrf-token` login response header
- `cookie_header` (str): Session cookies, formatted as a `Cookie` header
- `base_url` (str): The API base URL
- `year` (str): The academic year used to log in
- `mashov_auth_token` (str, optional): The `MashovAuthToken` cookie
- `csrf_cookie_token` (str, optional): The `Csrf-Token` cookie

## Error Handling

```python
from mashov import MashovClient, MashovLoginError, MashovRequestError, MashovError

async def safe_api_call():
    try:
        async with MashovClient(username, password, semel) as client:
            grades = await client.get_grades(student_id)
            return grades
            
    except MashovLoginError as e:
        print(f"Login failed: {e}")
        # Handle authentication errors
        
    except MashovRequestError as e:
        print(f"API request failed: {e}")
        # Handle request errors
        
    except MashovError as e:
        print(f"Mashov error: {e}")
        # Handle other Mashov-related errors
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle unexpected errors
```

### Exception Classes

- `MashovError` - Base exception for all pymashov errors
- `MashovLoginError` - Raised when login fails (HTTP error, timeout, missing `x-csrf-token` header or cookies), or when a session is needed and `auto_login=False`
- `MashovRequestError` - Raised when an API request times out, cannot be sent, or returns HTTP status 400 or higher

The `get_*` helpers call `response.json()`, so a response that isn't valid JSON raises a `json.JSONDecodeError` (a `ValueError`), not a `MashovError`.

## Logging

pymashov logs through the standard `logging` module under the `mashov.client` logger. Enable it like this:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("mashov.client").setLevel(logging.DEBUG)
```

At `INFO` level the log includes the username, school code and student IDs, and failed requests log the response body at `ERROR` level. Keep logs private. Raising the level to `WARNING` removes only the `INFO` lines: `ERROR` logs still include response bodies, student IDs and request paths that contain student IDs.

## Security Notes

- Don't hard-code credentials. Load them from environment variables or a secrets manager, and keep them out of version control.
- Treat everything the API returns as sensitive personal data about minors. Store it securely and delete it when you no longer need it.
- `MashovSession` holds live session tokens. Don't log, print or share it.
- Review your log settings before sharing logs (see [Logging](#logging)).
- Keep request volume low; pymashov uses the same API as the Mashov website and is meant for personal use, not bulk scraping.

## Development

```bash
git clone https://github.com/t0mer/pymashov.git
cd pymashov
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Project layout:

```
mashov/
├── __init__.py      # Public exports
├── client.py        # MashovClient
├── models.py        # MashovSession dataclass
├── session.py       # Older session dataclass (not used by the client)
└── exceptions.py    # Exception classes
setup.py             # Package metadata
```

There is no test suite yet.

Build the package with:

```bash
pip install build
python -m build
```

The `Publish pypi package` GitHub Actions workflow builds the package and uploads it to PyPI when a GitHub release is published, or when it is run manually. It uses the `PYPI_API_TOKEN` repository secret.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/t0mer/pymashov/blob/main/LICENSE) file for details.
<!-- TODO: verify license: LICENSE is Apache 2.0, but setup.py (and therefore PyPI) declares MIT -->

## Disclaimer

This is an unofficial API wrapper and is not affiliated with, endorsed by, or connected to Mashov or the Israeli Ministry of Education. Use at your own risk, and only with accounts you are entitled to access.

## Author

**Tomer Klein**
- Email: tomer.klein@gmail.com
- GitHub: [@t0mer](https://github.com/t0mer)

## Acknowledgments

- Built with [httpx](https://www.python-httpx.org/) for async HTTP requests
- Inspired by the need for programmatic access to student information

## Changelog

### 0.0.2 (2026-01-24)
- Added logging through the standard `logging` module
- Added error handling for timeouts and network errors (raised as `MashovLoginError` / `MashovRequestError`)

### 0.0.1 (2026-01-23, initial release)
- Basic authentication and session management
- Support for grades, timetable, homework, and behavior endpoints
- Mail conversations support
- Public schools endpoint
- Async/await support with httpx