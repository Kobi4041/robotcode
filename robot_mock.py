import time
from xgolib import XGO

# התחברות לרובוט
robot = XGO(port='/dev/ttyAMA0')

def test_360_spin(speed, duration):
    print(f"--- Testing Spin: Speed {speed}, Duration {duration}s ---")
    
    # הגדרות בסיסיות
    robot.pace('normal')
    robot.mark_time(20) # הרמת רגליים
    
    # התחלת הסיבוב
    robot.turn(speed) 
    
    # המתנה בזמן שהרובוט מסתובב
    time.sleep(duration)
    
    # עצירה מוחלטת
    robot.turn(0)
    robot.mark_time(0)
    robot.stop()
    
    print("--- Test Finished ---")

# כאן אתה יכול לשנות את הפרמטרים כדי למצוא את הדיוק
# אם ב-90 מעלות הוא לא מסיים סיבוב ב-4 שניות, נסה להעלות את המהירות או הזמן
test_360_spin(speed=90, duration=4.0)
