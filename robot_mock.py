from xgolib import XGO
dog = XGO(port='/dev/ttyAMA0')
dog.action(1) # אמור ליישר את הרגליים מיד
dog.translation(0,0,-50) # אמור להנמיך גוף
