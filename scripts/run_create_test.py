import sys
import traceback

try:
    with open("scripts/create_contabilidad_test_data.py", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, "scripts/create_contabilidad_test_data.py", "exec"), globals())
except Exception:
    traceback.print_exc()
    sys.exit(1)
print("SCRIPT_RUN_COMPLETED")
