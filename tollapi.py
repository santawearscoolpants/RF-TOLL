from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector

app = FastAPI()

# Database Connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # Set your MySQL password here
    database="toll_system"
)
cursor = conn.cursor(dictionary=True)

# Request Models
class TollPayment(BaseModel):
    plate_number: str
    amount: float

# Get Vehicle Toll Information
@app.get("/get-vehicle-info/{plate_number}")
def get_vehicle_info(plate_number: str):
    cursor.execute("""
        SELECT l.license_plate, t.rate AS toll_amount, 
               (CASE WHEN tr.license_plate_id IS NOT NULL THEN 'Flagged' ELSE 'Cleared' END) AS flag_status
        FROM license_plates l
        LEFT JOIN toll_rates t ON l.vehicle_type = t.vehicle_type
        LEFT JOIN transactions tr ON l.id = tr.license_plate_id AND tr.type = 'toll'
        WHERE l.license_plate = %s
    """, (plate_number,))
    
    vehicle = cursor.fetchone()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

# Deduct Toll Fee and Update Transactions
@app.post("/deduct-toll")
def deduct_toll(payment: TollPayment):
    # Get the rate from toll_rates table
    cursor.execute("""
        SELECT t.rate, l.id AS license_plate_id
        FROM license_plates l
        JOIN toll_rates t ON l.vehicle_type = t.vehicle_type
        WHERE l.license_plate = %s
    """, (payment.plate_number,))
    
    vehicle = cursor.fetchone()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    toll_rate = vehicle["rate"]
    plate_id = vehicle["license_plate_id"]
    
    if payment.amount < toll_rate:
        raise HTTPException(status_code=400, detail="Insufficient amount")

    # Deduct toll & Insert transaction
    cursor.execute("""
        INSERT INTO transactions (user_id, license_plate_id, amount, type, date, time)
        VALUES (%s, %s, %s, 'toll', CURDATE(), CURTIME())
    """, (1, plate_id, toll_rate))  # Assuming user_id = 1 for now

    conn.commit()
    
    return {"message": "Toll payment successful"}

# Flag Vehicle
@app.post("/flag-vehicle/{plate_number}")
def flag_vehicle(plate_number: str):
    cursor.execute("""
        UPDATE license_plates SET vehicle_type = 'flagged' 
        WHERE license_plate = %s
    """, (plate_number,))
    conn.commit()
    return {"message": "Vehicle flagged successfully"}
