import re
import sys
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


def mask_connection_string(s_conn: str) -> str:
    """Masks password in connection string for safe logging."""
    if not s_conn:
        return ""
    return re.sub(r"(?i)(Pwd\s*=\s*')[^']*(')", r"\g<1>***\g<2>", s_conn)


def format_com_error(e: Exception, s_prog_id: str = "V83.COMConnector") -> str:
    """Extracts a clear, diagnostic explanation from COM or standard Python exceptions."""
    bitness = "64-bit" if sys.maxsize > 2**32 else "32-bit"

    hr = getattr(e, 'hresult', None)
    msg = getattr(e, 'strerror', None)
    exc = getattr(e, 'excepinfo', None)

    # Some pywintypes.com_error instances pack attributes inside e.args
    if hasattr(e, 'args') and isinstance(e.args, (tuple, list)) and len(e.args) >= 3:
        if hr is None:
            hr = e.args[0]
        if msg is None:
            msg = e.args[1]
        if exc is None:
            exc = e.args[2]

    desc = ""
    source = ""
    if exc and isinstance(exc, (tuple, list)):
        if len(exc) > 1 and exc[1]:
            source = str(exc[1]).strip()
        if len(exc) > 2 and exc[2]:
            desc = str(exc[2]).strip()

    # 1. Invalid Class String (0x800401F3 / -2147221005) -> Component not registered
    if hr in (-2147221005, 0x800401F3) or (msg and "invalid class string" in str(msg).lower()):
        return (
            f"COM-клас '{s_prog_id}' не зареєстровано в системі Windows (Invalid class string). "
            f"Перевірте: 1) чи встановлено платформу 1С:Підприємство на цьому ПК; "
            f"2) чи зареєстровано бібліотеку comcntr.dll (команда: regsvr32 \"<шлях_до_1c>\\bin\\comcntr.dll\"); "
            f"3) чи збігається розрядність Python ({bitness}) та встановленої 1С (32/64-bit)."
        )

    # 2. Access Denied (0x80070005 / -2147024891)
    if hr in (-2147024891, 0x80070005) or (msg and "access is denied" in str(msg).lower()):
        res = "Відмовлено в доступі COM (E_ACCESSDENIED). Перевірте права DCOM або запустіть процес від імені адміністратора."
        if desc:
            res += f" Повідомлення: {desc}"
        return res

    # 3. Server Execution Failure (0x80080005 / -2146959355)
    if hr in (-2146959355, 0x80080005):
        res = "Збій запуску COM-сервера (CO_E_SERVER_EXEC_FAILURE)."
        if desc:
            res += f" Повідомлення: {desc}"
        return res

    # 4. If 1C Connect returned detailed exception text in excepinfo
    if desc:
        if source:
            return f"{desc} (Джерело: {source})"
        return desc

    # 5. Fallback to strerror or string representation
    if msg and msg != "Exception occurred.":
        if hr is not None:
            return f"{msg} (HRESULT: {hr})"
        return str(msg)

    return str(e)


class Connection:
    """Manages the COM connection to 1C and hosts managers to interact with different modules."""
    
    tz_kiev = pytz.timezone('Europe/Kiev')

    def __init__(
        self,
        s_oneCDatabasePathIn: Optional[str] = None,
        s_usernameIn: str = "",
        s_passwordIn: str = "",
        s_serverIn: Optional[str] = None,
        s_databaseNameIn: Optional[str] = None,
        s_progIdIn: str = "V83.COMConnector"
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
        self.s_prog_id = s_progIdIn

        if has_file:
            self.s_connection_string = f"File='{s_oneCDatabasePathIn}';Usr='{s_usernameIn}';Pwd='{s_passwordIn}';"
        else:
            self.s_connection_string = f"Srvr='{s_serverIn}';Ref='{s_databaseNameIn}';Usr='{s_usernameIn}';Pwd='{s_passwordIn}';"

        self.c_v8 = None
        self.s_last_error = ""
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
        s_passwordIn: str = "",
        s_progIdIn: str = "V83.COMConnector"
    ) -> "Connection":
        """Factory method to create a Connection to a file-based 1C database."""
        return cls(
            s_oneCDatabasePathIn=s_databasePathIn,
            s_usernameIn=s_usernameIn,
            s_passwordIn=s_passwordIn,
            s_progIdIn=s_progIdIn
        )

    @classmethod
    def create_server(
        cls,
        s_serverIn: str,
        s_databaseNameIn: str,
        s_usernameIn: str = "",
        s_passwordIn: str = "",
        s_progIdIn: str = "V83.COMConnector"
    ) -> "Connection":
        """Factory method to create a Connection to a 1C:Enterprise server cluster database."""
        return cls(
            s_usernameIn=s_usernameIn,
            s_passwordIn=s_passwordIn,
            s_serverIn=s_serverIn,
            s_databaseNameIn=s_databaseNameIn,
            s_progIdIn=s_progIdIn
        )

    def initiate_connection(self) -> None:
        """Establishes COM connection to 1C and caches price type references."""
        # Close existing connection if any
        if self.c_v8 is not None:
            log_sys("Closing existing connection before creating a new one...")
            self.close_connection()

        s_masked = mask_connection_string(self.s_connection_string)
        log_sys(f"Trying to initiate connection ({s_masked})...")
        try:
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            c_connector = win32com.client.Dispatch(self.s_prog_id)
        except Exception as e:
            s_reason = format_com_error(e, self.s_prog_id)
            log_sys(f"Failed to initialize COM connector '{self.s_prog_id}': {s_reason}", 1)
            self.s_last_error = s_reason
            self.c_v8 = None
            return

        try:
            self.c_v8 = c_connector.Connect(self.s_connection_string)
            if not self.c_v8:
                s_reason = "1C Connect() returned None (no active connection object)."
                log_sys(f"Failed to connect to 1C ({s_masked}): {s_reason}", 1)
                self.s_last_error = s_reason
                self.c_v8 = None
                return

            self.s_last_error = ""
            log_sys(f"Successfully connected to 1C ({s_masked}).")
        except Exception as e:
            s_reason = format_com_error(e, self.s_prog_id)
            log_sys(f"Failed to connect to 1C ({s_masked}): {s_reason}", 1)
            self.s_last_error = s_reason
            self.c_v8 = None
            return

        # Cache price types safely without aborting a valid connection on failure
        try:
            self._cache_price_types()
        except Exception as e:
            log_sys(f"Warning: Failed to cache price types after connection: {e}", 1)

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
