"""
Module 8 Student Enrollment App

Final version:
- Refactored backend into a database/store layer and service/manager layer
- Added a simple Streamlit UI layer
- Uses a simulated already-logged-in student
- No login, registration, passwords, or authentication system
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import streamlit as st


# -----------------------------
# Constants / Config
# -----------------------------

DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}

STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

AVAILABLE_COURSE_KEYS = [
    {
        "course_id": "MISY350",
        "course_name": "Python for Business Analytics",
        "instructor": "Dr. Rivera",
        "enrollment_key": "MISY350-SPRING",
    },
    {
        "course_id": "DATA210",
        "course_name": "Data Storytelling",
        "instructor": "Prof. Morgan",
        "enrollment_key": "DATA210-SPRING",
    },
    {
        "course_id": "WEB220",
        "course_name": "Web Apps With Streamlit",
        "instructor": "Dr. Chen",
        "enrollment_key": "WEB220-SPRING",
    },
]

SAMPLE_ENROLLMENTS = [
    ("u100", "maya.patel@example.edu", "MISY350", STATUS_ENROLLED),
    ("u100", "maya.patel@example.edu", "DATA210", STATUS_UNENROLLED),
    ("u101", "alex@example.edu", "MISY350", STATUS_ENROLLED),
    ("u102", "blair@example.edu", "WEB220", STATUS_ENROLLED),
]


# -----------------------------
# Database Layer
# -----------------------------

class EnrollmentStore:
    """Handles SQLite database work only."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    instructor TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_sample_data(self) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in AVAILABLE_COURSE_KEYS
                ],
            )

            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (
                    user_id, email, course_id, status
                )
                VALUES (?, ?, ?, ?)
                """,
                SAMPLE_ENROLLMENTS,
            )

    def rows_to_dicts(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_course_by_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        if not enrollment_key:
            return None

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (enrollment_key.strip().upper(),),
            ).fetchone()

        return dict(row) if row else None

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        if not user_id:
            return []

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
                """,
                (user_id, STATUS_ENROLLED),
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        if not user_id:
            return []

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()

        return self.rows_to_dicts(rows)

    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        if not user_id or not course_id:
            return None

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()

        return dict(row) if row else None

    def insert_or_reactivate_enrollment(
        self,
        user_id: str,
        email: str,
        course_id: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, STATUS_ENROLLED),
            )

    def update_enrollment_status(
        self,
        user_id: str,
        course_id: str,
        status: str,
    ) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (status, user_id, course_id),
            )

        return cursor.rowcount > 0

    def get_all_enrollment_records(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()

        return self.rows_to_dicts(rows)

    def export_database_snapshot(
        self,
        current_student: dict[str, str],
        path: Path = SNAPSHOT_PATH,
    ) -> None:
        snapshot = {
            "current_student": current_student,
            "available_course_keys": self.get_available_course_keys(),
            "enrollment_table": self.get_all_enrollment_records(),
        }

        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


# -----------------------------
# Service Layer
# -----------------------------

class EnrollmentManager:
    """Handles enrollment rules and student actions."""

    def __init__(self, store: EnrollmentStore) -> None:
        self.store = store

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        return self.store.get_available_course_keys()

    def enroll_with_key(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> Optional[dict[str, Any]]:
        if not user_id or not email or "@" not in email or not enrollment_key:
            return None

        course = self.store.get_course_by_key(enrollment_key)

        if not course:
            return None

        self.store.insert_or_reactivate_enrollment(
            user_id,
            email,
            course["course_id"],
        )

        return self.store.get_student_course_record(
            user_id,
            course["course_id"],
        )

    def soft_unenroll_student(self, user_id: str, course_id: str) -> bool:
        if not user_id or not course_id:
            return False

        return self.store.update_enrollment_status(
            user_id,
            course_id,
            STATUS_UNENROLLED,
        )

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        return self.store.get_student_enrollments(user_id)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        return self.store.get_student_enrollment_history(user_id)

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        summary = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }

        records = self.store.get_student_enrollment_history(user_id)

        for record in records:
            summary["total_records"] += 1
            status = record["status"]

            if status in summary:
                summary[status] += 1

        return summary


# -----------------------------
# UI Layer
# -----------------------------

class EnrollmentDashboard:
    """Handles Streamlit UI only."""

    def __init__(self, manager: EnrollmentManager, store: EnrollmentStore) -> None:
        self.manager = manager
        self.store = store

    def setup_session_state(self) -> None:
        if "page" not in st.session_state:
            st.session_state["page"] = "dashboard"

        if "role" not in st.session_state:
            st.session_state["role"] = "student"

        if "current_student" not in st.session_state:
            st.session_state["current_student"] = CURRENT_STUDENT

        if "selected_class" not in st.session_state:
            st.session_state["selected_class"] = None

        if "message" not in st.session_state:
            st.session_state["message"] = None

        if "message_type" not in st.session_state:
            st.session_state["message_type"] = None

    def show_message(self) -> None:
        message = st.session_state.get("message")
        message_type = st.session_state.get("message_type")

        if not message:
            return

        if message_type == "success":
            st.success(message)
        elif message_type == "warning":
            st.warning(message)
        elif message_type == "error":
            st.error(message)
        else:
            st.info(message)

    def set_message(self, message: str, message_type: str) -> None:
        st.session_state["message"] = message
        st.session_state["message_type"] = message_type

    def clear_message(self) -> None:
        st.session_state["message"] = None
        st.session_state["message_type"] = None

    def run(self) -> None:
        self.setup_session_state()

        st.set_page_config(
            page_title="Student Enrollment Dashboard",
            page_icon="🎓",
        )

        if st.session_state["role"] != "student":
            st.error("You do not have access to the student dashboard.")
            return

        if st.session_state["page"] == "dashboard":
            self.show_dashboard()
        elif st.session_state["page"] == "class_detail":
            self.show_class_detail()
        else:
            st.session_state["page"] = "dashboard"
            st.rerun()

    def show_dashboard(self) -> None:
        student = st.session_state["current_student"]
        user_id = student["user_id"]
        email = student["email"]

        st.title("🎓 Student Enrollment Dashboard")
        st.caption("View your classes, join a class, or open class details.")

        self.show_message()

        st.header("Current Student")
        st.write(f"**Name:** {student['name']}")
        st.write(f"**Email:** {student['email']}")

        summary = self.manager.get_student_summary(user_id)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Records", summary["total_records"])

        with col2:
            st.metric("Enrolled", summary[STATUS_ENROLLED])

        with col3:
            st.metric("Unenrolled", summary[STATUS_UNENROLLED])

        st.divider()

        st.header("Join a Class")

        with st.form("enrollment_form"):
            enrollment_key = st.text_input(
                "Enrollment Key",
                placeholder="Example: DATA210-SPRING",
            )
            submitted = st.form_submit_button("Enroll")

        if submitted:
            if not enrollment_key.strip():
                self.set_message("Please enter an enrollment key.", "warning")
                st.rerun()

            result = self.manager.enroll_with_key(
                user_id,
                email,
                enrollment_key,
            )

            if result:
                self.set_message(
                    f"You are now enrolled in {result['course_name']}.",
                    "success",
                )
            else:
                self.set_message(
                    "Enrollment failed. Check the key and try again.",
                    "error",
                )

            self.store.export_database_snapshot(CURRENT_STUDENT)
            st.rerun()

        st.divider()

        st.header("My Enrolled Classes")

        enrollments = self.manager.get_student_enrollments(user_id)

        if not enrollments:
            st.warning("You are not currently enrolled in any classes.")
        else:
            st.dataframe(enrollments, use_container_width=True)

            for enrollment in enrollments:
                with st.container(border=True):
                    st.subheader(enrollment["course_name"])
                    st.write(f"**Course ID:** {enrollment['course_id']}")
                    st.write(f"**Instructor:** {enrollment['instructor']}")
                    st.write(f"**Status:** {enrollment['status']}")

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "Go to Class",
                            key=f"go_{enrollment['course_id']}",
                        ):
                            st.session_state["selected_class"] = enrollment
                            st.session_state["page"] = "class_detail"
                            self.clear_message()
                            st.rerun()

                    with col2:
                        if st.button(
                            "Unenroll",
                            key=f"unenroll_{enrollment['course_id']}",
                        ):
                            success = self.manager.soft_unenroll_student(
                                user_id,
                                enrollment["course_id"],
                            )

                            if success:
                                self.set_message(
                                    f"You were unenrolled from {enrollment['course_name']}.",
                                    "success",
                                )
                            else:
                                self.set_message(
                                    "Unenroll failed.",
                                    "error",
                                )

                            self.store.export_database_snapshot(CURRENT_STUDENT)
                            st.rerun()

        st.divider()

        st.header("Available Enrollment Keys")
        available_keys = self.manager.get_available_course_keys()
        st.dataframe(available_keys, use_container_width=True)

    def show_class_detail(self) -> None:
        selected_class = st.session_state.get("selected_class")

        st.title("📘 Selected Class Page")

        if selected_class is None:
            st.warning("No class selected.")

            if st.button("Back to Dashboard"):
                st.session_state["page"] = "dashboard"
                st.rerun()

            return

        st.caption("Basic class information for the selected course.")

        with st.container(border=True):
            st.header(selected_class["course_name"])
            st.write(f"**Course ID:** {selected_class['course_id']}")
            st.write(f"**Instructor:** {selected_class['instructor']}")
            st.write(f"**Status:** {selected_class['status']}")
            st.write(f"**Enrolled At:** {selected_class['enrolled_at']}")

        if st.button("Back to Dashboard"):
            st.session_state["page"] = "dashboard"
            st.session_state["selected_class"] = None
            st.rerun()


# -----------------------------
# App Runner
# -----------------------------

def main() -> None:
    store = EnrollmentStore(DB_PATH)
    store.create_tables()
    store.seed_sample_data()
    store.export_database_snapshot(CURRENT_STUDENT)

    manager = EnrollmentManager(store)
    dashboard = EnrollmentDashboard(manager, store)
    dashboard.run()


if __name__ == "__main__":
    main()