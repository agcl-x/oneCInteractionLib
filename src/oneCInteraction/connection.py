from typing import Optional
import pythoncom
import pytz
import win32com.client
from .log import log_sys
from .nomenclature import NomenclatureManager
from .groups import GroupsManager
from .orders import OrdersManager
from .characteristics import CharacteristicsManager
from .categories import CategoriesManager
from .customers import CustomersManager
from .discounts import DiscountsManager
from .properties import PropertiesManager


class Connection:
    """Manages the COM connection to 1C and hosts managers to interact with different modules."""
    
    tz_kiev = pytz.timezone('Europe/Kiev')

    def __init__(
        self,
        s_oneCDatabasePathIn: Optional[str] = None,
        s_usernameIn: str = "",
        s_passwordIn: str = "",
        s_serverIn: Optional[str] = None,
        s_databaseNameIn: Optional[str] = None
    ):
        """Initializes connection details, saves required codes, and instantiates managers."""
        has_file = bool(s_oneCDatabasePathIn)
        has_server = bool(s_serverIn or s_databaseNameIn)

        if has_file and has_server:
            raise ValueError("Cannot specify both file database path and server parameters simultaneously.")
        if not has_file and not has_server:
            raise ValueError(
                "Either s_oneCDatabasePathIn (for file base) or both s_serverIn and s_databaseNameIn "
                "(for server base) must be provided."
            )
        if has_server and (not s_serverIn or not s_databaseNameIn):
            raise ValueError("Both s_serverIn and s_databaseNameIn must be provided for a server-based connection.")

        self.s_oneCDatabasePath = s_oneCDatabasePathIn
        self.s_server = s_serverIn
        self.s_database_name = s_databaseNameIn
        self.s_username = s_usernameIn
        self.s_password = s_passwordIn

        if has_file:
            self.s_connection_string = f"File='{s_oneCDatabasePathIn}';Usr='{s_usernameIn}';Pwd='{s_passwordIn}';"
        else:
            self.s_connection_string = f"Srvr='{s_serverIn}';Ref='{s_databaseNameIn}';Usr='{s_usernameIn}';Pwd='{s_passwordIn}';"

        self.c_v8 = None
        self.d_price_types = {}
        
        # Save codes to self for order creation
        self.s_warehouse_code = ""
        self.s_organisation_code = ""
        self.sl_price_types = ["Розничная", "Оптовая", "Закупочная"]

        # Managers (Composition)
        self.nomenclature = NomenclatureManager(self)
        self.groups = GroupsManager(self)
        self.orders = OrdersManager(self)
        self.characteristics = CharacteristicsManager(self)
        self.categories = CategoriesManager(self)
        self.customers = CustomersManager(self)
        self.discounts = DiscountsManager(self)
        self.properties = PropertiesManager(self)

    @classmethod
    def create_file(
        cls,
        s_databasePathIn: str,
        s_usernameIn: str = "",
        s_passwordIn: str = ""
    ) -> "Connection":
        """Factory method to create a Connection to a file-based 1C database."""
        return cls(
            s_oneCDatabasePathIn=s_databasePathIn,
            s_usernameIn=s_usernameIn,
            s_passwordIn=s_passwordIn
        )

    @classmethod
    def create_server(
        cls,
        s_serverIn: str,
        s_databaseNameIn: str,
        s_usernameIn: str = "",
        s_passwordIn: str = ""
    ) -> "Connection":
        """Factory method to create a Connection to a 1C:Enterprise server cluster database."""
        return cls(
            s_usernameIn=s_usernameIn,
            s_passwordIn=s_passwordIn,
            s_serverIn=s_serverIn,
            s_databaseNameIn=s_databaseNameIn
        )

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
        #pythoncom.CoUninitialize()
        log_sys("1C connection closed successfully.")
