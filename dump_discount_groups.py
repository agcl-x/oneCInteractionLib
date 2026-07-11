import sys
import os
from datetime import datetime

# Додаємо src до шляху пошуку модулів, щоб імпортувати локальну бібліотеку
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from oneCInteraction import Connection

# ================== НАЛАШТУВАННЯ З'ЄДНАННЯ З 1С ==================
# Вкажіть шлях до вашої бази даних 1С та облікові дані
ONE_C_DATABASE_PATH = r"C:\Path\To\Your\1C\Database" 
USERNAME = "Admin"
PASSWORD = "password"
# =================================================================

def main():
    if ONE_C_DATABASE_PATH == r"C:\Path\To\Your\1C\Database":
        print("[ПОПЕРЕДЖЕННЯ] Будь ласка, вкажіть реальний шлях до вашої бази 1С у змінній ONE_C_DATABASE_PATH.")
        return

    print(f"Ініціалізація з'єднання з базою 1С: {ONE_C_DATABASE_PATH}...")
    
    conn = Connection(
        s_oneCDatabasePathIn=ONE_C_DATABASE_PATH,
        s_usernameIn=USERNAME,
        s_passwordIn=PASSWORD
    )
    
    try:
        conn.initiate_connection()
        if not conn.c_v8:
            print("Не вдалося підключитися до 1С. Перевірте шлях до бази та облікові дані.")
            return
            
        print("З'єднання успішно встановлено!")
        print("Отримання активних груп знижок...")
        
        # Викликаємо менеджер знижок для отримання груп
        discount_groups = conn.discounts.get_active_groups()
        
        if not discount_groups:
            print("Активних груп знижок у базі не знайдено.")
            return
            
        print(f"\nЗнайдено {len(discount_groups)} активних груп знижок:")
        
        for i, dg in enumerate(discount_groups, 1):
            print(f"\n🔥 {i}. Група знижок: '{dg.s_name}'")
            print(f"   Код типу знижки (ТипСкидкиНаценки.Код): {dg.s_discount_type_code}")
            print(f"   Номер документа в 1С: {dg.s_document_number}")
            print(f"   Процент знижки: {dg.n_discount_percent}%")
            print(f"   Список товарів у цій групі ({len(dg.l_nomenclatures)} шт.):")
            
            for item in dg.l_nomenclatures:
                char_str = f" (Характеристика: '{item['char_name']}')" if item['char_name'] else ""
                print(f"     - [{item['code']}] {item['name']}{char_str} | UUID: {item['uuid']}")
                
    except Exception as e:
        print(f"Виникла помилка під час виконання: {e}")
    finally:
        print("\nЗакриття з'єднання з 1С...")
        conn.close_connection()
        print("З'єднання закрите.")

if __name__ == "__main__":
    main()
