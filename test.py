import traceback
try:
    import run_gita_demo
    run_gita_demo.run_demo()
except Exception as e:
    traceback.print_exc()
