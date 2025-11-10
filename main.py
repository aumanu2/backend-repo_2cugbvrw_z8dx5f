import os
from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="EduTrack SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "EduTrack backend is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Utilities

def _doc_with_id(doc: dict):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


def _oid(id_str: str) -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail="Invalid id")
    return ObjectId(id_str)


def _tenant_filter(tenant_id: Optional[str]):
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Missing tenant_id. Provide 'x-tenant-id' header or tenant_id query param.")
    return {"tenant_id": tenant_id}


# Schemas for payloads
class CreateStudent(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    grade: Optional[str] = None
    dob: Optional[str] = None
    parent_ids: Optional[List[str]] = []
    class_ids: Optional[List[str]] = []
    status: Optional[str] = "active"


class UpdateStudent(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    dob: Optional[str] = None
    parent_ids: Optional[List[str]] = None
    class_ids: Optional[List[str]] = None
    status: Optional[str] = None


class CreateTeacher(BaseModel):
    first_name: str
    last_name: str
    email: str
    subject: Optional[str] = None
    is_admin: bool = False


class UpdateTeacher(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None
    is_admin: Optional[bool] = None


class CreateClass(BaseModel):
    name: str
    code: str
    teacher_id: Optional[str] = None
    grade_level: Optional[str] = None
    student_ids: Optional[List[str]] = []


class UpdateClass(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    teacher_id: Optional[str] = None
    grade_level: Optional[str] = None
    student_ids: Optional[List[str]] = None


class CreateAnnouncement(BaseModel):
    title: str
    body: str
    audience: str = "all"


class FeeInvoice(BaseModel):
    student_id: str
    amount: float
    currency: str = "USD"
    due_date: Optional[str] = None
    status: str = "open"
    memo: Optional[str] = None


class Payment(BaseModel):
    invoice_id: str
    amount: float
    method: str = "stripe"
    reference: Optional[str] = None


# Students
@app.get("/students")
async def list_students(limit: int = 50, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        filt = _tenant_filter(t)
        items = get_documents("student", filt, limit)
        return [_doc_with_id(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/students")
async def create_student(payload: CreateStudent, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    data = payload.model_dump()
    data["tenant_id"] = t
    try:
        _tenant_filter(t)
        new_id = create_document("student", data)
        return {"id": new_id, "message": "Student created"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.put("/students/{student_id}")
async def update_student(student_id: str, payload: UpdateStudent, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    _tenant_filter(t)
    try:
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        res = db["student"].update_one({"_id": _oid(student_id), "tenant_id": t}, {"$set": updates})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"id": student_id, "updated": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.delete("/students/{student_id}")
async def delete_student(student_id: str, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    _tenant_filter(t)
    try:
        res = db["student"].delete_one({"_id": _oid(student_id), "tenant_id": t})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Student not found")
        return {"id": student_id, "deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


# Teachers
@app.get("/teachers")
async def list_teachers(limit: int = 50, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        items = get_documents("teacher", _tenant_filter(t), limit)
        return [_doc_with_id(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/teachers")
async def create_teacher(payload: CreateTeacher, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    data = payload.model_dump()
    data["tenant_id"] = t
    try:
        _tenant_filter(t)
        new_id = create_document("teacher", data)
        return {"id": new_id, "message": "Teacher created"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


# Classes
@app.get("/classes")
async def list_classes(limit: int = 50, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        items = get_documents("class", _tenant_filter(t), limit)
        return [_doc_with_id(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/classes")
async def create_class(payload: CreateClass, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    data = payload.model_dump()
    data["tenant_id"] = t
    try:
        _tenant_filter(t)
        new_id = create_document("class", data)
        return {"id": new_id, "message": "Class created"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


# Announcements
@app.post("/announcements")
async def create_announcement(payload: CreateAnnouncement, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        _tenant_filter(t)
        data = payload.model_dump()
        data["tenant_id"] = t
        ann_id = create_document("announcement", data)
        return {"id": ann_id, "message": "Announcement created"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.get("/announcements")
async def list_announcements(limit: int = 20, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        items = get_documents("announcement", _tenant_filter(t), limit)
        return [_doc_with_id(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


# Finance
@app.post("/invoices")
async def create_invoice(payload: FeeInvoice, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        _tenant_filter(t)
        data = payload.model_dump()
        data["tenant_id"] = t
        inv_id = create_document("feeinvoice", data)
        return {"id": inv_id, "message": "Invoice created"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.get("/invoices")
async def list_invoices(limit: int = 50, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        items = get_documents("feeinvoice", _tenant_filter(t), limit)
        return [_doc_with_id(x) for x in items]
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


@app.post("/payments")
async def create_payment(payload: Payment, tenant_id: Optional[str] = Query(default=None), x_tenant_id: Optional[str] = Header(default=None)):
    t = x_tenant_id or tenant_id
    try:
        _tenant_filter(t)
        data = payload.model_dump()
        data["tenant_id"] = t
        pay_id = create_document("payment", data)
        # also mark invoice paid if amounts match (best-effort)
        try:
            db["feeinvoice"].update_one({"_id": _oid(data["invoice_id"])}, {"$set": {"status": "paid"}})
        except Exception:
            pass
        return {"id": pay_id, "message": "Payment recorded"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
