#!/usr/bin/env python3
import os
import sqlite3
import random
from datetime import date, timedelta
import argparse

from faker import Faker

DB_FILENAME = 'friends_birthdays.db'
MAX_AGE = 80  # максимальный возраст в годах

def create_connection(db_path):
    """Подключаемся к SQLite (файл создаётся автоматически)."""
    try:
        return sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print(f"Ошибка подключения к базе: {e}")
        exit(1)

def create_table(conn):
    """Создаём таблицу friends, если её ещё нет."""
    sql = """
    CREATE TABLE IF NOT EXISTS friends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        surname TEXT NOT NULL,
        name TEXT NOT NULL,
        patronymic TEXT,
        birth_date TEXT NOT NULL
    );
    """
    conn.execute(sql)
    conn.commit()

def random_birthdate(min_age=0, max_age=MAX_AGE):
    """
    Возвращает случайную дату рождения так,
    чтобы возраст был от min_age до max_age лет.
    """
    today = date.today()
    # грубая оценка: 1 год ≈ 365 дней
    start = today - timedelta(days=max_age * 365)
    end   = today - timedelta(days=min_age * 365)
    span  = (end - start).days
    return start + timedelta(days=random.randrange(span + 1))

def populate(conn, count):
    fake = Faker('ru_RU')
    entries = []
    for _ in range(count):
        gender = random.choice(['male', 'female'])
        if gender == 'male':
            fn = fake.first_name_male()
            ln = fake.last_name_male()
            pn = fake.middle_name_male()
        else:
            fn = fake.first_name_female()
            ln = fake.last_name_female()
            pn = fake.middle_name_female()
        bd = random_birthdate().isoformat()  # YYYY-MM-DD
        entries.append((ln, fn, pn, bd))

    conn.executemany(
        "INSERT INTO friends(surname, name, patronymic, birth_date) VALUES (?, ?, ?, ?)",
        entries
    )
    conn.commit()
    print(f"Добавлено {count} друзей в базу.")

def main():
    parser = argparse.ArgumentParser(
        description="Создаёт БД друзей и заполняет её случайными ФИО и датами рождения."
    )
    parser.add_argument(
        '--count', '-n',
        type=int, default=100,
        help="Сколько записей сгенерировать (по умолчанию 100)"
    )
    args = parser.parse_args()

    db_path = os.path.join(os.getcwd(), DB_FILENAME)
    conn = create_connection(db_path)
    create_table(conn)
    populate(conn, args.count)
    conn.close()
    print(f"База '{DB_FILENAME}' готова.")

if __name__ == '__main__':
    main()
