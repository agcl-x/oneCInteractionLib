import sys
import os
from datetime import datetime, timezone
import pytz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from oneCInteraction import Connection, Customer, Order, OrderItem, Variety, Price

def test_order_date_preparation():
    conn = Connection("fake_path", "fake_user", "fake_pwd")
    tz_kiev = conn.tz_kiev

    # 1. Test with Django UTC datetime (e.g. 14:02 UTC = 17:02 Kyiv in summer)
    utc_dt = datetime(2026, 9, 25, 14, 2, 0, tzinfo=timezone.utc)
    order = Order(dt_dateIn=utc_dt)
    
    # Simulate the date resolution from OrdersManager.push
    local_dt = order.dt_date.astimezone(tz_kiev)
    assert local_dt.hour == 17
    assert local_dt.minute == 2
    
    com_dt = local_dt.replace(tzinfo=timezone.utc)
    assert com_dt.hour == 17
    assert com_dt.minute == 2
    assert com_dt.tzinfo == timezone.utc

    # 2. Test COM marshaling with ADODB Recordset (simulates pywin32 VT_DATE transmission)
    import win32com.client
    rs = win32com.client.Dispatch('ADODB.Recordset')
    rs.Fields.Append('dt', 7) # 7 = adDate (VT_DATE)
    rs.Open()
    rs.AddNew()
    rs.Fields('dt').Value = com_dt
    
    val = rs.Fields('dt').Value
    # COM must retain 17:02 without subtracting local timezone offset
    assert val.hour == 17
    assert val.minute == 2
    print("Success: COM date correctly retained Kyiv wall-clock time (17:02:00) without -3 hour offset!")

if __name__ == "__main__":
    test_order_date_preparation()
    print("All date handling tests passed!")
