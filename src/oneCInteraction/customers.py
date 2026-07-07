from .log import log_sys
from . import structures

class CustomersManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def create(self, c_customerIn) -> str:
        """
        Creates a new counterparty in 1C using the parameters from a Customer object.
        Returns the code of the created counterparty or empty string if failed.
        """
        if not self.c_v8:
            log_sys("Failed to create customer: No connection to 1C.", 1)
            return ""

        try:
            log_sys("Creating new customer/counterparty in 1C...")
            c_newCustomer = self.c_v8.Catalogs.Контрагенты.CreateItem()

            # Construct PIB/Name
            parts = [c_customerIn.s_customerSurname, c_customerIn.s_customerName, c_customerIn.s_customerPatronymic]
            s_pib = " ".join([p for p in parts if p]).strip()
            
            if not s_pib:
                s_pib = f"Customer_{c_customerIn.s_customerId}"

            c_newCustomer.Наименование = s_pib

            # Try to set ПолноеНаименование
            try:
                c_newCustomer.ПолноеНаименование = s_pib
            except Exception:
                pass

            # Try to set individual attributes if they exist
            try:
                c_newCustomer.Телефон = c_customerIn.s_customerPhone
            except Exception:
                pass
            
            try:
                c_newCustomer.Адрес = c_customerIn.s_customerAddress
            except Exception:
                pass

            # Set Comment with ID and contact info
            s_comment = f"ID: {c_customerIn.s_customerId}"
            if c_customerIn.s_customerPhone:
                s_comment += f"\nPhone: {c_customerIn.s_customerPhone}"
            if c_customerIn.s_customerAddress:
                s_comment += f"\nAddress: {c_customerIn.s_customerAddress}"
            
            try:
                c_newCustomer.Комментарий = s_comment
            except Exception:
                pass

            c_newCustomer.Write()

            s_code = self.c_v8.String(c_newCustomer.Код)
            log_sys(f"Customer '{s_pib}' successfully created with code: {s_code}")
            
            # Update customer structure with the new code
            c_customerIn.s_customerCode = s_code

            # Create default contract
            self.ensure_default_contract(c_newCustomer.Ссылка)

            return s_code

        except Exception as e:
            log_sys(f"Failed to create counterparty: {e}", 1)
            return ""

    def get(self, s_codeIn: str):
        """Retrieves and parses a customer/counterparty by its 1C code."""
        if not self.c_v8:
            log_sys("Failed to get customer: No connection to 1C. Returning None", 1)
            return None

        if len(s_codeIn) < 1:
            log_sys(f"Failed to get customer: Wrong code format ({s_codeIn}). Returning None", 1)
            return None

        try:
            log_sys(f"Searching for customer with code: {s_codeIn}...")
            c_clientRef = self.c_v8.Catalogs.Контрагенты.FindByCode(s_codeIn)

            if c_clientRef.IsEmpty():
                log_sys(f"Customer with code {s_codeIn} not found in 1C.", 1)
                return None

            log_sys("Customer found. Extracting data...")
            c_clientObj = c_clientRef.GetObject()

            # Try to get direct attributes if they exist
            s_phone = ""
            try:
                s_phone = c_clientObj.Телефон
            except Exception:
                pass

            s_address = ""
            try:
                s_address = c_clientObj.Адрес
            except Exception:
                pass

            # Parse from comment
            s_comment = ""
            try:
                s_comment = c_clientObj.Комментарий
            except Exception:
                pass

            s_customerId = s_comment  # Fallback if comment is just the ID
            if s_comment and ("\n" in s_comment or ":" in s_comment):
                lines = s_comment.split("\n")
                for line in lines:
                    if line.startswith("ID:") or line.startswith("Telegram ID:"):
                        s_customerId = line.split(":", 1)[1].strip()
                    elif line.startswith("Phone:") and not s_phone:
                        s_phone = line.split(":", 1)[1].strip()
                    elif line.startswith("Address:") and not s_address:
                        s_address = line.split(":", 1)[1].strip()

            s_pib = ""
            try:
                s_pib = c_clientObj.Наименование
            except Exception:
                pass

            s_surname = ""
            s_name = ""
            s_patronymic = ""
            if s_pib:
                parts = s_pib.split()
                if len(parts) >= 1:
                    s_surname = parts[0]
                if len(parts) >= 2:
                    s_name = parts[1]
                if len(parts) >= 3:
                    s_patronymic = " ".join(parts[2:])

            c_customer = structures.Customer(
                s_customerIdIn=s_customerId,
                s_customerNameIn=s_name,
                s_customerSurnameIn=s_surname,
                s_customerPatronymicIn=s_patronymic,
                s_customerPhoneIn=s_phone,
                s_customerAddressIn=s_address,
                s_customerCodeIn=s_codeIn
            )
            return c_customer

        except Exception as e:
            log_sys(f"Error occurred while retrieving customer {s_codeIn}: {e}", 1)
            return None

    def ensure_default_contract(self, c_clientRef):
        """Ensures that the counterparty has a default contract. Creates one if missing."""
        try:
            if c_clientRef.ОсновнойДоговорКонтрагента.IsEmpty():
                log_sys("Counteragent has no default contract. Creating one...")
                c_contract = self.c_v8.Catalogs.ДоговорыКонтрагентов.CreateItem()
                c_contract.Владелец = c_clientRef
                c_contract.Наименование = "Основной договор"
                
                if self.c_connection.s_organisation_code:
                    c_orgRef = self.c_v8.Catalogs.Организации.FindByCode(self.c_connection.s_organisation_code)
                    if not c_orgRef.IsEmpty():
                        c_contract.Организация = c_orgRef

                try:
                    c_contract.ВидДоговора = self.c_v8.Enums.ВидыДоговоров.СПокупателем
                except Exception:
                    try:
                        c_contract.ВидДоговора = self.c_v8.Перечисления.ВидыДоговоров.СПокупателем
                    except Exception:
                        pass
                
                try:
                    c_currencyRef = self.c_v8.Catalogs.Валюты.FindByCode("980")
                    if not c_currencyRef.IsEmpty():
                        c_contract.ВалютаВзаиморасчетов = c_currencyRef
                except Exception:
                    pass

                c_contract.Write()
                
                c_clientObj = c_clientRef.GetObject()
                c_clientObj.ОсновнойДоговорКонтрагента = c_contract.Ссылка
                c_clientObj.Write()
                log_sys("Default contract successfully created and assigned.")
        except Exception as e:
            log_sys(f"Failed to ensure default contract: {e}", 1)
