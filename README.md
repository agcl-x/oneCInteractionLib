# 1C Interaction Library (`oneCInteraction`)

A modular Python library for interacting with «1C:Enterprise» databases via a COM connection (`V83.COMConnector`). It enables seamless integration of 1C with websites, Telegram bots, or other external services.

## Features
- **Full COM Connection Support** via `win32com`.
- **Nomenclature and Categories Management**: retrieve group trees, batch load products, prices, and stock balances across warehouses.
- **Product Characteristics**: read variant properties from information registers or parse text descriptions.
- **Images**: download product images directly from the 1C database to the local disk.
- **Order Management**: create customer orders, track statuses, and update document comments with customer contact details.
- **Smart Logging**: automatically creates log files in the directory of the host project importing the library.

---

## Installation

This library requires a Windows operating system with the 1C:Enterprise 8.3 platform installed and the `pywin32` package.

Install the package:
```bash
pip install oneCInteraction.
```

---

## Architecture Overview

The library is built on the principle of composition: the main `Connection` class initializes the COM connection and hosts specialized managers:
- `Connection.nomenclature` (`NomenclatureManager`) — manages products and images.
- `Connection.groups` (`GroupsManager`) — manages group hierarchy.
- `Connection.categories` (`CategoriesManager`) — manages nomenclature categories.
- `Connection.characteristics` (`CharacteristicsManager`) — reads properties of product variants.
- `Connection.orders` (`OrdersManager`) — handles creation and updates of customer orders.

---

## Detailed Class and Function Reference

### 1. Main Class `Connection`
The `Connection` class (located in [connection.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/connection.py)) manages the COM connection to 1C and holds general settings.

#### Constructor:
```python
def __init__(self, s_oneCDatabasePathIn: str, s_usernameIn: str, s_passwordIn: str)
```
- `s_oneCDatabasePathIn` (str): Absolute path to the file-based 1C database on disk.
- `s_usernameIn` (str): 1C username.
- `s_passwordIn` (str): 1C password.

#### Key Attributes:
- `s_warehouse_code` (str): 1C warehouse code for new orders.
- `s_counteragent_code` (str): 1C counteragent (customer) code for new orders.
- `s_organisation_code` (str): 1C organization code for new orders.
- `sl_price_types` (list): List of price type names to cache automatically (defaults to `["Розничная", "Оптовая"]`).
- `c_v8`: The active 1C COM connection object (equals `None` if not connected).

#### Methods:
- `initiate_connection() -> None`: Establishes the COM connection to 1C using `V83.COMConnector` and caches price type references.
- `close_connection() -> None`: Closes the connection and releases COM resources.
- `get_price_type_ref(s_nameIn: str)`: Returns the 1C COM reference for a price type by its name.

---

### 2. Data Structures (`structures.py`)
All data models are defined in [structures.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/structures.py).

#### `Nomenclature`
Represents a product.
- `s_name` (str): Product name.
- `s_article` (str): Product article (SKU).
- `s_description` (str): Product description.
- `l_variety` (list of `Variety`): List of available variants/characteristics of the product.
- `s_unit` (str): Unit of measurement (defaults to `"шт."`).
- `s_parent_uuid` (str): UUID of the parent group/category.
- `s_uuid` (str): Unique identifier (UUID) of the product in 1C.
- `s_code` (str): 1C product code.
- `l_images` (list): List of image UUIDs associated with the product in 1C.

#### `Variety`
Represents a product variant with specific prices and stock levels.
- `n_priceRetail` (float): Retail price for the variant.
- `n_priceOpt` (float): Wholesale price for the variant.
- `n_pricePurchase` (float): Purchase price for the variant.
- `d_count` (dict): Stock balances by warehouse in the format `{"Warehouse Name": quantity}`.
- `l_characteristics` (list of `Characteristic`): List of characteristics for the variant.

#### `Characteristic`
A key-value pair for a variant property.
- `s_name` (str): Property name (e.g., `"Color"`).
- `s_value` (str): Property value (e.g., `"Red"`).

#### `Group`
A product group (category).
- `s_name` (str): Group name.
- `l_subGroups` (list of `Group`): List of subgroups.
- `l_nomenclatures` (list of `Nomenclature`): List of products inside the group.
- `c_ref`: COM reference to the group in 1C.
- `s_code` (str): 1C group code.
- `s_uuid` (str): UUID of the group in 1C.

#### `Category`
Represents a nomenclature category (e.g. `ВидНоменклатуры` / `КатегорияНоменклатуры`).
- `s_name` (str): Category name.
- `l_nomenclatures` (list of `Nomenclature`): List of products inside the category.
- `c_ref`: COM reference to the category in 1C.
- `s_code` (str): 1C category code.
- `s_uuid` (str): UUID of the category in 1C.

#### `Customer`
Information about the buyer.
- `s_customerTelegramId` (str): Telegram ID of the user.
- `s_customerPIB` (str): Full name (PIB) of the customer.
- `s_customerPhone` (str): Customer's phone number.
- `s_customerAddress` (str): Delivery address of the customer.

#### `OrderItem`
An item in the order.
- `s_productArticle` (str): Product article (SKU).
- `s_productPropertie` (str): Selected characteristic name (if any).
- `n_productCount` (int): Quantity of items.

#### `Order`
A buyer's order.
- `c_orderCustomer` (`Customer`): Customer details object.
- `l_orderItemsList` (list of `OrderItem`): List of ordered items.
- `s_TTN` (str): Waybill number (TTN).
- `s_status` (str): Status of the order in 1C.
- `s_date` (str): Order creation date (automatically generated).
- `n_orderCode` (str / int): Order number in 1C.

Calling `str(order_obj)` returns a nicely formatted HTML string suitable for sending to a Telegram bot.

---

### 3. Nomenclature Manager `NomenclatureManager` (`Connection.nomenclature`)
Defined in [nomenclature.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/nomenclature.py).

- `get(s_articleIn: str = "", s_nameIn: str = "", s_codeIn: str = "") -> Nomenclature | None`
  Searches for and returns a product by its article, name, or code. Fetches retail/wholesale prices, stock balances by warehouses, and characteristics.
- `get_images(c_productObjIn: Nomenclature, s_imageDirIn: str = None) -> list`
  Downloads all attached images for a product from 1C. Saves them in the specified directory `s_imageDirIn` (defaults to `data/images`). Returns a list of the saved filenames (e.g., `["[uuid]_0.jpg"]`).
- `get_by_group(c_groupRefIn) -> list`
  Batch fetches all products within a specific 1C group. Using optimized COM queries, this method minimizes DB requests and operates significantly faster than calling `get()` sequentially in a loop.
- `get_by_category(c_categoryIn, s_attributeNameIn: str = "ВидНоменклатуры", s_catalogNameIn: str = "ВидыНоменклатуры") -> list`
  Batch fetches all products within a specific 1C category (by default using the `ВидНоменклатуры` attribute in the `ВидыНоменклатуры` catalog). `c_categoryIn` can be a COM reference object or a string representing the category name.

---

### 4. Category Manager `GroupsManager` (`Connection.groups`)
Defined in [groups.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/groups.py).

- `get_tree(sl_ignoredCategoriesNamesIn: list) -> list`
  Builds the hierarchical category tree from 1C. Branches whose names are listed in `sl_ignoredCategoriesNamesIn` are excluded along with all their subcategories.
- `get_by_name(s_nameIn: str) -> Group | None`
  Finds a reference to a group by its exact name in 1C.
- `get_full_path(c_groupRefIn) -> str`
  Builds the full text hierarchy path to a category, traversing up to the root parent (e.g., `"Clothing > Men's > Shoes"`).

---

### 5. Categories Manager `CategoriesManager` (`Connection.categories`)
Defined in [categories.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/categories.py).

- `get(s_codeIn: str = "", s_nameIn: str = "") -> Category | None`
  Finds a single Category by its code or name in the `ВидыНоменклатуры` catalog.
- `create(s_nameIn: str) -> Category | None`
  Creates a new Category with the specified name in `Справочник.ВидыНоменклатуры` and returns it.

---

### 6. Characteristics Manager `CharacteristicsManager` (`Connection.characteristics`)
Defined in [characteristics.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/characteristics.py).

- `parse_name(s_charNameIn: str) -> list` *(static method)*
  Parses a characteristic name string (e.g., `"Size: L"` or `"Color - Red"`) and returns a list of `Characteristic` objects.
- `get(c_charRefIn, s_charNameIn: str = "") -> list`
  Queries characteristic properties from the `ЗначенияСвойствОбъектов` register. If no properties are found, falls back to parsing the name string via `parse_name()`.
- `fetch_batch(l_charRefsIn: list) -> dict`
  Batch fetches property values for a list of characteristic references.

---

### 7. Orders Manager `OrdersManager` (`Connection.orders`)
Defined in [orders.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/orders.py).

- `push(c_orderObjIn: Order) -> str`
  Creates a new `"Заказ покупателя"` (Buyer's Order) document in 1C.
  - Automatically queries the warehouse, counteragent, and organization based on codes specified in the `Connection` object.
  - Sets the retail price type, document currency (Hryvnia, code `"980"`), and organization's primary bank account.
  - Adds products from the order, queries the exact price for the specific characteristic selected, and computes totals.
  - Attempts to post the document (`Posting`). If posting fails, it writes the document in draft/save mode (`Write`).
  - Returns the number of the created document in 1C (or an empty string on error).
- `get(s_codeIn: str) -> Order | None`
  Retrieves a buyer's order by its 1C document number and parses it into an `Order` object. The comment field is parsed to retrieve the Telegram ID.
- `get_today() -> list`
  Returns a list of all today's orders created for the configured bot counteragent (filtered by current date and counteragent code).
- `update_info(c_orderObjIn: Order) -> bool`
  Updates the comment field of the order in 1C. Writes a formatted string to the comment field:
  `"[Full Name] [Phone] [Telegram ID] [Waybill/TTN] [Status]"`

---

### 8. Logging (`log.py`)
Defined in [log.py](file:///c:/Users/agcl/PycharmProjects/oneCInteractionLib/src/oneCInteraction/log.py).

All actions are logged automatically. The library resolves the root directory of the project that imported it and stores log files in the relative path `log/system/[calling_module_name].log`.
- `log_sys(message, errorFlag = 0)` — The main logging utility. If `errorFlag=1`, prepends an `[ERROR]` tag.

---

## Usage Example

### Complete Workflow (Fetching Products and Creating an Order)

```python
from oneCInteraction import Connection, Customer, Order, OrderItem

# 1. Initialize Connection
c_conn = Connection(
    s_oneCDatabasePathIn="C:\\1C_Bases\\ShopDB",
    s_usernameIn="AdminBot",
    s_passwordIn="secure_password"
)

# 2. Configure 1C Default Codes
c_conn.s_warehouse_code = "000000001"  # Warehouse code
c_conn.s_counteragent_code = "000000045"  # Bot customer/counteragent code
c_conn.s_organisation_code = "000000001"  # Organization code

# 3. Establish connection to 1C
c_conn.initiate_connection()

if c_conn.c_v8:
    try:
        # 4. Fetch Category Tree
        ignored_cats = ["Archive", "System"]
        categories = c_conn.groups.get_tree(ignored_cats)
        print(f"Loaded {len(categories)} root categories.")

        # 5. Get products from the first category
        first_group = categories[0]
        products = c_conn.nomenclature.get_by_group(first_group.c_ref)
        print(f"Found products in group {first_group.s_name}: {len(products)}")

        for p in products[:3]:
            print(f"Product: {p.s_name} | SKU: {p.s_article}")
            if p.l_variety:
                v = p.l_variety[0]
                print(f"  Price: {v.n_priceRetail} UAH | Stocks: {v.d_count}")

            # Download product images
            images = c_conn.nomenclature.get_images(p, s_imageDirIn="static/images")
            print(f"  Downloaded images: {images}")

        # 6. Create a New Order
        customer = Customer(
            s_customerTelegramIdIn="123456789",
            s_customerPIBIn="John Doe",
            s_customerPhoneIn="+380991112233",
            s_customerAddressIn="Kyiv, Nova Poshta Warehouse #1"
        )

        items = [
            OrderItem(
                s_productArticleIn="ART-1024",
                s_productPropertieIn="Size: L, Color: Blue",
                n_productCountIn=2
            )
        ]

        new_order = Order(
            c_orderCustomerIn=customer,
            l_orderItemsListIn=items
        )

        # Submit the order to 1C
        order_number = c_conn.orders.push(new_order)
        if order_number:
            print(f"Order created successfully in 1C! Order Number: {order_number}")

            # Update TTN and status details
            new_order.n_orderCode = order_number
            new_order.s_TTN = "20450011223344"
            new_order.s_status = "Shipped"
            c_conn.orders.update_info(new_order)

            # Output order details formatted as HTML string
            print(str(new_order))

    finally:
        # Always clean up and close the connection
        c_conn.close_connection()
else:
    print("Failed to connect to 1C database.")
```
