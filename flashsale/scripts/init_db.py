#!/usr/bin/env python3
"""Database initialization script"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import engine, Base
from app.models.product import Product
from app.models.order import Order

def init_database():
    print("Initializing database...")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
        
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal
        
        db = SessionLocal()
        
        existing_product = db.query(Product).first()
        if not existing_product:
            test_product = Product(
                name="Flash Sale - iPhone 15 Pro",
                price=5999.00,
                stock=100,
                description="Limited time flash sale!"
            )
            db.add(test_product)
            db.commit()
            print("Test product added!")
        
        db.close()
        print("Database initialization completed!")
        
    except Exception as e:
        print("Database initialization failed:", str(e))
        sys.exit(1)

if __name__ == "__main__":
    init_database()