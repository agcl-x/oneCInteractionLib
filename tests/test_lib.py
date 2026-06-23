import sys
import os

# Ensure the library is importable from src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Configure console output to support Ukrainian/Cyrillic characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from oneCInteraction import Connection, Customer, Order, OrderItem, Nomenclature, Variety, Characteristic, Group
    from oneCInteraction.log import log_sys, log_usr, archiveLog, clearLog, LOGS_DIR
    
    print("Success: Imported Connection and all structures successfully from oneCInteraction!")
    
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
    
    # Test logging functionality
    print(f"Logs directory configured at: {LOGS_DIR}")
    
    # Write some logs
    log_usr("User logged successfully", errorflag=0, user_id="test_user")
    log_sys("System started successfully", errorFlag=0)
    
    # Check that the log directory and files were created relative to the running test script
    expected_usr_log = os.path.join(LOGS_DIR, 'user', 'test_user.log')
    expected_sys_log = os.path.join(LOGS_DIR, 'system', 'test_lib.log')
    
    assert os.path.exists(expected_usr_log), f"User log file not found at {expected_usr_log}"
    assert os.path.exists(expected_sys_log), f"System log file not found at {expected_sys_log}"
    print("Success: Log files were successfully created at the target directory.")
    
    # Test archiving
    archiveLog()
    expected_archive = os.path.join(os.path.dirname(LOGS_DIR), 'logDumps')
    print(f"Checking for archive in: {expected_archive}")
    assert os.path.exists(expected_archive), "Archive directory not found."
    
    # Clean up logs
    clearLog()
    assert not os.path.exists(LOGS_DIR), "Logs were not cleared."
    print("Success: Log functions tested and verified.")
    
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
