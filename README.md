# 1C Interaction Library (`onec_interaction`)

A modular, clean Python library for interacting with 1C:Enterprise databases using Windows COM connection (`V83.COMConnector`).

## Installation

Install the package locally in editable mode:
```bash
pip install -e .
```

## Basic Usage

```python
from onec_interaction import Connection, Customer, Order, OrderItem

# 1. Initialize the connection details
c_conn = Connection(
    s_oneCDatabasePathIn="C:\\Path\\To\\1C\\Database",
    s_usernameIn="admin",
    s_passwordIn="password"
)

# 2. Configure default parameters
c_conn.s_warehouse_code = "WH001"
c_conn.s_counteragent_code = "CA001"
c_conn.s_organisation_code = "ORG001"

# 3. Establish COM connection
c_conn.initiate_connection()

# 4. Use composition managers
# Fetch product details
c_product = c_conn.nomenclature.get(s_articleIn="ART001")
print(f"Product: {c_product.s_name}, Price: {c_product.l_variety[0].n_price}")

# Close connection when done
c_conn.close_connection()
```
