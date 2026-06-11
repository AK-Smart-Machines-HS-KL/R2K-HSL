import argparse
import importlib.util
import os
import sys

# Importiere deine bestehende Score-Funktion
from score_function import calculate_score

def load_worldstate(testcase_number: int):
    """
    Lädt die worldstate.py dynamisch aus dem nummerierten Ordner, 
    da Standard-Imports bei Ordnern, die mit Zahlen beginnen, fehlschlagen.
    """
    folder_name = f"{testcase_number}.Testcase"
    file_path = os.path.join(folder_name, "worldstate.py")

    if not os.path.exists(file_path):
        print(f"FEHLER: Die Datei {file_path} existiert nicht.")
        sys.exit(1)

    # Dynamischer Import über den absoluten/relativen Dateipfad
    spec = importlib.util.spec_from_file_location("dynamic_testcase", file_path)
    testcase_module = importlib.util.module_from_spec(spec)
    sys.modules["dynamic_testcase"] = testcase_module
    spec.loader.exec_module(testcase_module)

    # Suche im geladenen Modul nach einer Instanz der WorldState Klasse
    for attr_name in dir(testcase_module):
        attr = getattr(testcase_module, attr_name)
        # Wir prüfen über den Klassennamen, um zirkuläre Imports zu vermeiden
        if type(attr).__name__ == "WorldState":
            return attr

    print(f"FEHLER: Kein instanziiertes WorldState-Objekt in {file_path} gefunden.")
    sys.exit(1)

if __name__ == "__main__":
    # Kommandozeilen-Parser einrichten
    parser = argparse.ArgumentParser(description="Bewertet einen Roboter-Fussball WorldState.")
    parser.add_argument(
        "--testcase", 
        type=int, 
        required=True, 
        help="Die Nummer des Testcases (z.B. 1 für '1.Testcase')"
    )
    args = parser.parse_args()

    print(f"Lade Testcase {args.testcase}...")
    
    # 1. State laden
    current_state = load_worldstate(args.testcase)
    
    # 2. Score berechnen
    final_score = calculate_score(current_state)
    
    # 3. Ergebnis ausgeben
    print("-" * 30)
    print(f"ERGEBNIS TESTCASE {args.testcase}: Score = {final_score}")
    print("-" * 30)