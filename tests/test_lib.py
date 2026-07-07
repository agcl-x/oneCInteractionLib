import sys
import os

# Ensure the library is importable from src directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Configure console output to support Ukrainian/Cyrillic characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from datetime import datetime
    from oneCInteraction import Connection, Customer, Order, OrderItem, Nomenclature, Variety, Price, Characteristic, Group, Category
    from oneCInteraction.log import log_sys, LOGS_DIR
    
    print("Success: Imported Connection and all structures successfully from oneCInteraction!")
    
    # Test instantiation of structures
    c_cust = Customer(s_customerIdIn="123456789", s_customerNameIn="Ivan", s_customerSurnameIn="Ivanov", s_customerPhoneIn="+380991112233")
    print("Success: Customer instantiated.")
    
    c_item = OrderItem(s_productArticleIn="ART001", s_productPropertieIn="Red", n_productCountIn=2)
    print("Success: OrderItem instantiated.")
    
    c_order = Order(c_orderCustomerIn=c_cust, l_orderItemsListIn=[c_item], n_orderCodeIn=1001)
    print("Success: Order instantiated.")
    print(f"Order __str__ test:\n{c_order}")
    
    # Test Price & Variety structures
    c_retail_price = Price(n_value=120.5, dt_assigned=datetime.now(), s_type="Розничная")
    c_opt_price = Price(n_value=100.0, dt_assigned=datetime.now(), s_type="Оптовая")
    c_purchase_price = Price(n_value=80.0, dt_assigned=datetime.now(), s_type="Закупочная")
    
    c_var = Variety(
        c_priceRetailIn=c_retail_price,
        c_priceOptIn=c_opt_price,
        d_countIn={"Основной склад": 10},
        l_characteristicsIn=[],
        c_pricePurchaseIn=c_purchase_price
    )
    assert c_var.c_priceRetail.n_value == 120.5
    assert c_var.c_priceOpt.n_value == 100.0
    assert c_var.c_pricePurchase.n_value == 80.0
    assert c_var.c_priceRetail.s_type == "Розничная"
    print("Success: Price and Variety instantiated and verified.")
    
    c_nom = Nomenclature(s_nameIn="Product 1", s_articleIn="ART001", l_varietyIn=[c_var])
    print("Success: Nomenclature instantiated.")
    
    c_cat = Category(s_categoryNameIn="Shoes", l_nomenclaturesIn=[c_nom])
    print("Success: Category instantiated.")
    
    c_conn = Connection(s_oneCDatabasePathIn="test_db", s_usernameIn="admin", s_passwordIn="pass")
    print("Success: Connection class instantiated.")
    
    assert c_conn.nomenclature is not None
    assert c_conn.groups is not None
    assert c_conn.orders is not None
    assert c_conn.characteristics is not None
    assert c_conn.categories is not None
    assert c_conn.customers is not None
    print("Success: Checked all composition managers exist.")

    # Test CustomersManager when connection is not active
    cust_res = c_conn.customers.get("CUST001")
    assert cust_res is None, f"Expected None since connection is not active, got {cust_res}"

    cust_create_res = c_conn.customers.create(c_cust)
    assert cust_create_res == "", f"Expected empty string since connection is not active, got {cust_create_res}"
    print("Success: CustomersManager.get and create tested with no active connection.")
    
    # Test NomenclatureManager.search function (connection not active, should return [])
    res = c_conn.nomenclature.search("ворота")
    assert isinstance(res, list), f"Expected list, got {type(res)}"
    assert len(res) == 0, f"Expected empty list because connection is not active, got {res}"
    
    res_name = c_conn.nomenclature.search("ворота", s_searchByIn="name")
    assert isinstance(res_name, list) and len(res_name) == 0
    
    res_article = c_conn.nomenclature.search("sm1111", s_searchByIn="article")
    assert isinstance(res_article, list) and len(res_article) == 0
    
    print("Success: NomenclatureManager.search tested with no active connection (with and without s_searchByIn parameters).")
    
    # Test logging functionality
    print(f"Logs directory configured at: {LOGS_DIR}")
    
    # Write some logs
    log_sys("System started successfully", errorFlag=0)
    
    # Check that the log directory and files were created relative to the running test script
    expected_sys_log = os.path.join(LOGS_DIR, 'system', 'test_lib.log')
    
    assert os.path.exists(expected_sys_log), f"System log file not found at {expected_sys_log}"
    print("Success: Log files were successfully created at the target directory.")
    
    # Clean up logs
    if os.path.exists(expected_sys_log):
        os.remove(expected_sys_log)
    try:
        os.rmdir(os.path.join(LOGS_DIR, 'system'))
        os.rmdir(LOGS_DIR)
    except Exception:
        pass
    print("Success: Log functions tested and verified.")
    
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
