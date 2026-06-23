import sys
import os

# Ensure the library is importable from current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure console output to support Ukrainian/Cyrillic characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from onec_interaction import Connection, Customer, Order, OrderItem, Nomenclature, Variety, Characteristic, Group
    print("Success: Imported Connection and all structures successfully from onec_interaction!")
    
    # Test instantiation of structures
    c_cust = Customer(s_customerTelegramIdIn="123456789", s_customerPIBIn="Ivan Ivanov", s_customerPhoneIn="+380991112233")
    print("Success: Customer instantiated.")
    
    c_item = OrderItem(s_productArticleIn="ART001", s_productPropertieIn="Red", n_productCountIn=2)
    print("Success: OrderItem instantiated.")
    
    c_order = Order(c_orderCustomerIn=c_cust, l_orderItemsListIn=[c_item], n_orderCodeIn=1001)
    print("Success: Order instantiated.")
    print(f"Order __str__ test:\n{c_order}")
    
    c_nom = Nomenclature(s_nameIn="Product 1", s_articleIn="ART001", l_varietyIn=[])
    print("Success: Nomenclature instantiated.")
    
    c_conn = Connection(s_oneCDatabasePathIn="test_db", s_usernameIn="admin", s_passwordIn="pass")
    print("Success: Connection class instantiated.")
    
    assert c_conn.nomenclature is not None
    assert c_conn.groups is not None
    assert c_conn.orders is not None
    assert c_conn.characteristics is not None
    print("Success: Checked all composition managers exist.")
    
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
