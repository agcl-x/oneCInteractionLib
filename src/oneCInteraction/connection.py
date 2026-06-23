import sys
import pythoncom
import pytz
from .log import log_sys

# Handle path for win32com on local environments
PYWIN32_PATH = r'C:\Users\Администратор\AppData\Local\Programs\Python\Python314\Lib\site-packages\pywin32_system32'
if PYWIN32_PATH not in sys.path:
    sys.path.append(PYWIN32_PATH)

import win32com.client

from .nomenclature import NomenclatureManager
from .groups import GroupsManager
from .orders import OrdersManager
from .characteristics import CharacteristicsManager

class Connection:
    """Manages the COM connection to 1C and hosts managers to interact with different modules."""
    
    tz_kiev = pytz.timezone('Europe/Kiev')

    def __init__(
        self,
        s_oneCDatabasePathIn: str,
        s_usernameIn: str,
        s_passwordIn: str
    ):
        """Initializes connection details, saves required codes, and instantiates managers."""
        self.s_connection_string = f"File='{s_oneCDatabasePathIn}';Usr='{s_usernameIn}';Pwd='{s_passwordIn}';"
        self.c_v8 = None
        self.d_price_types = {}
        
        # Save codes to self for order creation
        self.s_warehouse_code = ""
        self.s_counteragent_code = ""
        self.s_organisation_code = ""
        self.sl_price_types = ["Розничная", "Оптовая"]

        # Managers (Composition)
        self.nomenclature = NomenclatureManager(self)
        self.groups = GroupsManager(self)
        self.orders = OrdersManager(self)
        self.characteristics = CharacteristicsManager(self)

    def initiate_connection(self) -> None:
        """Establishes COM connection to 1C and caches price type references."""
        log_sys('Trying to initiate connection...')
        try:
            pythoncom.CoInitialize()
            c_connector = win32com.client.Dispatch("V83.COMConnector")
            self.c_v8 = c_connector.Connect(self.s_connection_string)
            log_sys("Successfully connected to 1C.")
            self._cache_price_types()
        except Exception as e:
            log_sys(f"Failed to connect to 1C: {e}")
            self.c_v8 = None

    def _cache_price_types(self) -> None:
        """Caches references for retail and wholesale price types from 1C catalog."""
        if not self.c_v8:
            return
        
        log_sys("Caching price types...")
        for s_ptName in self.sl_price_types:
            self.get_price_type_ref(s_ptName)

    def get_price_type_ref(self, s_nameIn: str):
        """Returns the cached price type reference, or queries 1C if not yet cached."""
        if s_nameIn in self.d_price_types:
            return self.d_price_types[s_nameIn]
        
        if not self.c_v8:
            return None

        try:
            c_query = self.c_v8.NewObject("Query")
            c_query.Text = "SELECT Ссылка FROM Справочник.ТипыЦенНоменклатуры WHERE Наименование = &Name"
            c_query.SetParameter("Name", s_nameIn)
            c_ptExec = c_query.Execute()
            if c_ptExec is not None and not c_ptExec.IsEmpty():
                c_ptRes = c_ptExec.Select()
                c_ptRes.Next()
                self.d_price_types[s_nameIn] = c_ptRes.Ссылка
                return c_ptRes.Ссылка
            else:
                log_sys(f"Cannot find price type '{s_nameIn}' in 1C constants/catalog", 1)
                return self.c_v8.String("")
        except Exception as e:
            log_sys(f"Error fetching price type '{s_nameIn}': {e}", 1)
            return self.c_v8.String("")

    def close_connection(self) -> None:
        """Closes the COM connection and uninitializes PythonCOM."""
        log_sys("Closing 1C connection...")
        self.c_v8 = None
        pythoncom.CoUninitialize()
        log_sys("1C connection closed successfully.")
