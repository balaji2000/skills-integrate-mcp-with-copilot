"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
import sqlite3

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities"
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=current_dir / "static"),
    name="static",
)

DB_PATH = current_dir / "activity_data.sqlite"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                activity_name TEXT NOT NULL,
                email TEXT NOT NULL,
                PRIMARY KEY (activity_name, email),
                FOREIGN KEY(activity_name) REFERENCES activities(name)
            )
            """
        )

        existing = conn.execute("SELECT COUNT(1) FROM activities").fetchone()[0]
        if existing == 0:
            for name, details in DEFAULT_ACTIVITIES.items():
                conn.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (name, details["description"], details["schedule"], details["max_participants"]),
                )
                for email in details["participants"]:
                    conn.execute(
                        "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
                        (name, email),
                    )


def load_activities():
    with get_db_connection() as conn:
        activities = {}
        rows = conn.execute("SELECT * FROM activities ORDER BY name").fetchall()
        for row in rows:
            participants = [
                participant["email"]
                for participant in conn.execute(
                    "SELECT email FROM participants WHERE activity_name = ? ORDER BY email",
                    (row["name"],),
                ).fetchall()
            ]
            activities[row["name"]] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": participants,
            }
        return activities


def activity_exists(activity_name: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        return row is not None


def participant_count(activity_name: str):
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT COUNT(1) FROM participants WHERE activity_name = ?",
            (activity_name,),
        ).fetchone()[0]


def is_signed_up(activity_name: str, email: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        ).fetchone()
        return row is not None


init_db()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    if not activity_exists(activity_name):
        raise HTTPException(status_code=404, detail="Activity not found")

    if is_signed_up(activity_name, email):
        raise HTTPException(status_code=400, detail="Student is already signed up")

    current_participants = participant_count(activity_name)
    with get_db_connection() as conn:
        max_participants = conn.execute(
            "SELECT max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()["max_participants"]

        if current_participants >= max_participants:
            raise HTTPException(status_code=400, detail="Activity is full")

        conn.execute(
            "INSERT INTO participants (activity_name, email) VALUES (?, ?)",
            (activity_name, email),
        )

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    if not activity_exists(activity_name):
        raise HTTPException(status_code=404, detail="Activity not found")

    if not is_signed_up(activity_name, email):
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM participants WHERE activity_name = ? AND email = ?",
            (activity_name, email),
        )

    return {"message": f"Unregistered {email} from {activity_name}"}
