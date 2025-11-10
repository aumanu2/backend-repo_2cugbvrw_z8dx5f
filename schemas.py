"""
Database Schemas for EduTrack SaaS

Each Pydantic model corresponds to a MongoDB collection.
Collection name is the lowercase of the class name.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date


class Student(BaseModel):
    first_name: str = Field(..., description="Student first name")
    last_name: str = Field(..., description="Student last name")
    email: Optional[EmailStr] = Field(None, description="Student email")
    grade: Optional[str] = Field(None, description="Grade or year level")
    dob: Optional[date] = Field(None, description="Date of birth")
    parent_ids: List[str] = Field(default_factory=list, description="Linked parent IDs")
    class_ids: List[str] = Field(default_factory=list, description="Enrolled class IDs")
    status: Literal["active", "inactive"] = Field("active", description="Student status")


class Parent(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    student_ids: List[str] = Field(default_factory=list, description="Linked students")


class Teacher(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    subject: Optional[str] = None
    is_admin: bool = False


class Class(BaseModel):
    name: str = Field(..., description="Class name, e.g., Algebra I")
    code: str = Field(..., description="Unique class code")
    teacher_id: Optional[str] = None
    grade_level: Optional[str] = None
    student_ids: List[str] = Field(default_factory=list)


class Enrollment(BaseModel):
    student_id: str
    class_id: str
    status: Literal["enrolled", "completed", "dropped"] = "enrolled"


class Progress(BaseModel):
    student_id: str
    class_id: Optional[str] = None
    metric: Literal["assignment", "quiz", "exam", "attendance", "behavior", "custom"] = "assignment"
    title: Optional[str] = Field(None, description="Optional title for the metric entry")
    score: Optional[float] = Field(None, ge=0, le=100, description="Percentage score if applicable")
    notes: Optional[str] = None


class Announcement(BaseModel):
    title: str
    body: str
    audience: Literal["all", "students", "parents", "teachers"] = "all"


class WaitlistLead(BaseModel):
    email: EmailStr
    role: Literal["school admin", "teacher", "parent", "student", "other"] = "school admin"
    note: Optional[str] = None
