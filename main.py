# --- עדכון ב-Mock (למקרה שאתה בסימולציה) ---
if IS_SIM:
    class XGO_Mock:
        def action(self, cmd_id): print(f"ACTION: {cmd_id}")
        def stop(self): print("STOP")
        def translation(self, x, y, z): print(f"TRANSLATION: z={z}")
        def attitude(self, r, p, y): print(f"ATTITUDE: p={p}")
    robot = XGO_Mock()

# ... (כל שאר הקוד שלך עד הבלוק של הביצוע הפיזי) ...

    # --- ביצוע פיזי (מצבים סטטיים נעולים) ---
    if final_cmd != last_final_cmd:
        if robot:
            if final_cmd == "LIE DOWN":
                # מצב סטטי: מוריד את הגוף למינימום ונשאר שם
                robot.translation(0, 0, -60)
                robot.attitude(0, 0, 0)
                print(">>> Command: STATIC LIE DOWN")
                
            elif final_cmd == "ATTENTION":
                # מצב סטטי: עמידה זקופה וגבוהה
                robot.translation(0, 0, 0)
                robot.attitude(0, 0, 0)
                robot.action(1) # איפוס מפרקים לעמידה
                print(">>> Command: STATIC ATTENTION")
                
            elif final_cmd == "READY":
                # מצב ניטרלי: גובה רגיל ועצירת תנועה
                robot.translation(0, 0, 0)
                robot.stop()
                print(">>> Command: READY / IDLE")

        last_final_cmd = final_cmd
