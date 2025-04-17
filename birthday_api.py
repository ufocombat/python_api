# birthday_api.py
"""
Asynchronous CRUD API for friends' birthdays using FastAPI and SQLite.

Dependencies:
  pip install fastapi uvicorn aiosqlite pydantic

Run:
  uvicorn birthday_api:app --reload
"""
import os
import aiosqlite
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, constr, validator
from datetime import date

DB_FILE = os.path.join(os.path.dirname(__file__), 'friends_birthdays.db')

app = FastAPI(title="Friends Birthday API")

# Pydantic models
table_name = 'friends'

class FriendBase(BaseModel):
    surname: constr(strip_whitespace=True, min_length=1)
    name: constr(strip_whitespace=True, min_length=1)
    patronymic: Optional[constr(strip_whitespace=True)] = None
    birth_date: date

class FriendCreate(FriendBase):
    pass

class FriendUpdate(BaseModel):
    surname: Optional[constr(strip_whitespace=True, min_length=1)] = None
    name: Optional[constr(strip_whitespace=True, min_length=1)] = None
    patronymic: Optional[constr(strip_whitespace=True)] = None
    birth_date: Optional[date] = None

    @validator('*')
    def at_least_one(cls, v, values, **kwargs):
        if not any(values.values()) and v is None:
            raise ValueError('At least one field must be provided')
        return v

class Friend(FriendBase):
    id: int = Field(..., gt=0)

# DB helper
def get_db():
    return aiosqlite.connect(DB_FILE)

@app.on_event("startup")
async def startup():
    # Ensure table exists
    async with get_db() as db:
        await db.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                surname TEXT NOT NULL,
                name TEXT NOT NULL,
                patronymic TEXT,
                birth_date TEXT NOT NULL
            );
        """
        )
        await db.commit()

@app.get("/friends", response_model=List[Friend])
async def list_friends():
    async with get_db() as db:
        cursor = await db.execute(f"SELECT id, surname, name, patronymic, birth_date FROM {table_name}")
        rows = await cursor.fetchall()
        return [Friend(id=r[0], surname=r[1], name=r[2], patronymic=r[3], birth_date=r[4]) for r in rows]

@app.get("/friends/{friend_id}", response_model=Friend)
async def get_friend(friend_id: int):
    async with get_db() as db:
        cursor = await db.execute(
            f"SELECT id, surname, name, patronymic, birth_date FROM {table_name} WHERE id = ?", (friend_id,)
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
        return Friend(id=row[0], surname=row[1], name=row[2], patronymic=row[3], birth_date=row[4])

@app.post("/friends", response_model=Friend, status_code=status.HTTP_201_CREATED)
async def create_friend(friend: FriendCreate):
    async with get_db() as db:
        cursor = await db.execute(
            f"INSERT INTO {table_name}(surname, name, patronymic, birth_date) VALUES (?, ?, ?, ?)",
            (friend.surname, friend.name, friend.patronymic, friend.birth_date.isoformat())
        )
        await db.commit()
        new_id = cursor.lastrowid
        return Friend(id=new_id, **friend.dict())

@app.put("/friends/{friend_id}", response_model=Friend)
async def update_friend(friend_id: int, data: FriendUpdate):
    # Fetch existing
    async with get_db() as db:
        cursor = await db.execute(f"SELECT id, surname, name, patronymic, birth_date FROM {table_name} WHERE id = ?", (friend_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
        existing = dict(id=row[0], surname=row[1], name=row[2], patronymic=row[3], birth_date=row[4])
        updated = existing.copy()
        update_data = data.dict(exclude_unset=True)
        updated.update({k: (v.isoformat() if isinstance(v, date) else v) for k, v in update_data.items()})
        # Apply update
        await db.execute(
            f"""
            UPDATE {table_name}
            SET surname = ?, name = ?, patronymic = ?, birth_date = ?
            WHERE id = ?
            """,
            (updated['surname'], updated['name'], updated['patronymic'], updated['birth_date'], friend_id)
        )
        await db.commit()
        return Friend(**updated)

@app.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_friend(friend_id: int):
    async with get_db() as db:
        cursor = await db.execute(f"DELETE FROM {table_name} WHERE id = ?", (friend_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Friend not found")
        return None
