# pymashov

[![PyPI version](https://badge.fury.io/py/pymashov.svg)](https://badge.fury.io/py/pymashov)
[![Python Versions](https://img.shields.io/pypi/pyversions/pymashov.svg)](https://pypi.org/project/pymashov/)
[![License](https://img.shields.io/github/license/t0mer/pymashov.svg)](https://github.com/t0mer/pymashov/blob/main/LICENSE)

Unofficial async Python API wrapper for Mashov - the Israeli education system's student and parent portal.

## Features

- ✨ **Async/await support** - Built with modern Python async patterns using `httpx`
- 🔐 **Secure authentication** - Handles CSRF tokens and session management
- 📚 **Comprehensive API coverage** - Access grades, timetables, homework, behavior records, and more
- 🎯 **Type hints** - Full type annotation support for better IDE experience
- 🚀 **Easy to use** - Simple, intuitive interface with context manager support

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
- httpx >= 0.25

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
        year="2026"  # Optional, defaults to current year
    ) as client:
        # Login is handled automatically
        
        # Get student grades
        student_id = "YOUR_STUDENT_ID"
        grades = await client.get_grades(student_id)
        print(f"Grades: {grades}")

asyncio.run(main())
```

## Usage Examples

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
        print(f"Logged in successfully!")
        print(f"CSRF Token: {session.csrf_header_token}")
        
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

### Get Weekly Timetable

```python
async def get_weekly_schedule(client, student_id):
    """Fetch student's weekly timetable."""
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
        for grade in grades[:5]:  # Show last 5 grades
            print(f"  • {grade.get('subject', 'N/A')}: {grade.get('grade', 'N/A')}")
        
        # Get today's timetable
        print("\n📅 TODAY'S SCHEDULE:")
        timetable = await client.get_timetable(student_id)
        # Process and display timetable...
        
        # Get pending homework
        print("\n📝 PENDING HOMEWORK:")
        homework = await client.get_homework(student_id)
        for hw in homework[:5]:  # Show next 5 assignments
            print(f"  • {hw.get('subject', 'N/A')}: {hw.get('description', 'N/A')}")
            print(f"    Due: {hw.get('dueDate', 'N/A')}")
        
        # Get recent behavior records
        print("\n⭐ RECENT BEHAVIOR:")
        behavior = await client.get_behavior(student_id)
        for record in behavior[:3]:  # Show last 3 records
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
- `username` (str): User ID number
- `password` (str): User password
- `semel` (str): School code
- `year` (str, optional): Academic year (default: "2026")
- `base_url` (str, optional): API base URL (default: "https://web.mashov.info")
- `timeout` (float, optional): Request timeout in seconds (default: 20.0)
- `auto_login` (bool, optional): Auto-login on first request (default: True)

**Methods:**

#### `async login() -> MashovSession`
Manually login and obtain session credentials.

#### `async close() -> None`
Close the HTTP client session.

#### `async get_grades(student_id: str) -> Any`
Get student grades.

#### `async get_timetable(student_id: str) -> Any`
Get student's weekly timetable.

#### `async get_homework(student_id: str) -> Any`
Get homework assignments.

#### `async get_behavior(student_id: str) -> Any`
Get behavior/discipline records.

#### `async get_conversations(skip: int = 0, take: int = 20) -> Any`
Get mail conversations from inbox.

#### `async get_schools() -> Any`
Get list of available schools (public endpoint, no authentication required).

#### `async request(method: str, path: str, **kwargs) -> httpx.Response`
Low-level authenticated request method for custom API calls.

#### `async public_request(method: str, path: str, **kwargs) -> httpx.Response`
Low-level public request method (no authentication).

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

## Exception Classes

- `MashovError` - Base exception for all pymashov errors
- `MashovLoginError` - Raised when login fails or authentication is missing
- `MashovRequestError` - Raised when an API request fails

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial API wrapper and is not affiliated with, endorsed by, or connected to Mashov or the Israeli Ministry of Education. Use at your own risk.

## Author

**Tomer Klein**
- Email: tomer.klein@gmail.com
- GitHub: [@t0mer](https://github.com/t0mer)

## Acknowledgments

- Built with [httpx](https://www.python-httpx.org/) for async HTTP requests
- Inspired by the need for programmatic access to student information

## Changelog

### 0.0.1 (Initial Release)
- Basic authentication and session management
- Support for grades, timetable, homework, and behavior endpoints
- Mail conversations support
- Public schools endpoint
- Async/await support with httpx