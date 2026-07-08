from datetime import datetime
from .log import log_sys
from . import structures

class OrdersManager:
    def __init__(self, c_connectionIn):
        self.c_connection = c_connectionIn

    @property
    def c_v8(self):
        return self.c_connection.c_v8

    def push(self, c_orderObjIn) -> str:
        """Pushes a new customer order to 1C database, returning the created order number or empty string."""
        if not self.c_v8:
            log_sys("Failed to push order: No connection to 1C. Returning None", 1)
            return None
            
        if not self.c_connection.s_warehouse_code or not self.c_connection.s_counteragent_code or not self.c_connection.s_organisation_code:
            log_sys("Failed to push order: No warehouse code and/or counteragent code and/or organisation code. Returning None", 1)
            return None

        try:
            c_newOrder = self.c_v8.Documents.ЗаказПокупателя.CreateDocument()
            log_sys("Client order was created. Start adding metadata")
            
            # Warehouse
            try:
                log_sys("Trying to get warehouse...")
                c_warehouseRef = self.c_v8.Catalogs.Склады.FindByCode(self.c_connection.s_warehouse_code)
                if c_warehouseRef.IsEmpty():
                    log_sys(f"Can't find main warehouse by code: {self.c_connection.s_warehouse_code}. Returning \"\"", 1)
                c_newOrder.СкладГруппа = c_warehouseRef
            except Exception as e:
                log_sys(f"Failed main warehouse finding: {e}. Returning \"\"", 1)
                return ""

            # Date
            log_sys("Trying to add date to order...")
            c_newOrder.Дата = datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)
            log_sys("Date successfully added")

            # Client / Counteragent
            c_clientRef = None
            c_customer = getattr(c_orderObjIn, "c_orderCustomer", None)
            b_isBotCounteragent = False
            
            if c_customer:
                log_sys("Customer structure found in order. Trying to resolve counteragent in 1C...")
                try:
                    # 1. Try by code if present
                    if c_customer.s_customerCode:
                        log_sys(f"Searching customer by code: {c_customer.s_customerCode}")
                        c_ref = self.c_v8.Catalogs.Контрагенты.FindByCode(c_customer.s_customerCode)
                        if not c_ref.IsEmpty():
                            c_clientRef = c_ref
                            log_sys("Customer found by code.")
                    
                    # 2. If not found or code is empty, create a new counterparty
                    if not c_clientRef:
                        log_sys("Customer not found in 1C. Attempting to create a new counterparty...")
                        s_newCode = self.c_connection.customers.create(c_customer)
                        if s_newCode:
                            c_ref = self.c_v8.Catalogs.Контрагенты.FindByCode(s_newCode)
                            if not c_ref.IsEmpty():
                                c_clientRef = c_ref
                                log_sys("New customer created and resolved.")
                except Exception as e:
                    log_sys(f"Failed to resolve customer: {e}. Falling back to bot counteragent...", 1)
            
            # Fallback to Bot Counteragent if customer resolution failed or customer wasn't provided
            if not c_clientRef or c_clientRef.IsEmpty():
                b_isBotCounteragent = True
                log_sys(f"Falling back to bot counteragent with code: {self.c_connection.s_counteragent_code}")
                try:
                    c_clientRef = self.c_v8.Catalogs.Контрагенты.FindByCode(self.c_connection.s_counteragent_code)
                    if c_clientRef.IsEmpty():
                        log_sys(f"Can't find bot contragent by code: {self.c_connection.s_counteragent_code}. Returning \"\"", 1)
                        return ""
                except Exception as e:
                    log_sys(f"Failed to resolve bot contragent: {e}. Returning \"\"", 1)
                    return ""

            try:
                c_newOrder.Контрагент = c_clientRef
                self.c_connection.customers.ensure_default_contract(c_clientRef)
                c_newOrder.ДоговорКонтрагента = c_clientRef.ОсновнойДоговорКонтрагента
                log_sys("Contragent and ContragentContract successfully added to order")
            except Exception as e:
                log_sys(f"Failed adding contragent/contract reference to order: {e}. Returning \"\"", 1)
                return ""

            # Organisation
            log_sys("Trying to add organisation to order...")
            c_newOrder.Организация = self.c_v8.Catalogs.Организации.FindByCode(self.c_connection.s_organisation_code)
            if c_newOrder.Организация.IsEmpty():
                log_sys("Failed adding organisation. Returning \"\"", 1)
                return ""
            log_sys("Organisation successfully added to order")

            # Bank Account
            log_sys("Trying to get organisation bank account...")
            c_orgAcc = c_newOrder.Организация.ОсновнойБанковскийСчет
            if not c_orgAcc.IsEmpty():
                log_sys("Bank account successfully got. Trying to add to order...")
                try:
                    c_newOrder.СтруктурнаяЕдиница = c_orgAcc
                    log_sys(f"Bank account successfully added to order: {c_orgAcc.Description}")
                except Exception as e:
                    log_sys(f"Failed adding bank account to order: {e}", 1)
            else:
                log_sys("Failed getting bank account", 1)

            # Currency
            log_sys("Trying to get currency...")
            c_currencyRef = self.c_v8.Catalogs.Валюты.FindByCode("980")
            if c_currencyRef.IsEmpty():
                log_sys("Failed getting currency", 1)
            c_newOrder.ВалютаДокумента = c_currencyRef
            log_sys("Currency successfully added to order")

            # Price Type
            log_sys("Trying to get price type...")
            s_price_type_name = getattr(c_orderObjIn, "s_price_type", "")
            if not s_price_type_name:
                s_price_type_name = "Розничная"
            c_priceTypeRef = self.c_connection.get_price_type_ref(s_price_type_name)
            c_newOrder.ТипЦен = c_priceTypeRef
            log_sys(f"Price type ({s_price_type_name}) successfully added to order")

            # Exchange rate settings
            c_newOrder.КурсВзаиморасчетов = 1.0
            c_newOrder.КратностьВзаиморасчетов = 1
            log_sys("КурсВзаиморасчетов, КратностьВзаиморасчетов successfully added to order")

            # Order Items List
            log_sys("Parsing orderItemList")
            for c_item in c_orderObjIn.l_orderItemsList:
                log_sys(f"Trying to get nomenclature by code ({c_item.s_productCode})")
                c_nomRef = self.c_v8.Catalogs.Номенклатура.FindByCode(c_item.s_productCode)

                if c_nomRef.IsEmpty():
                    log_sys("Nomenclature not found, skipping...")
                    continue

                log_sys("Nomenclature successfully fetched")
                
                # Extract characteristic description from variety if present
                s_itemProp = ""
                if getattr(c_item, "c_variety", None) is not None:
                    parts = []
                    for char in c_item.c_variety.l_characteristics:
                        if char.s_name == "Характеристика":
                            parts.append(char.s_value)
                        else:
                            parts.append(f"{char.s_name}: {char.s_value}")
                    s_itemProp = ", ".join(parts)
                    
                log_sys(f"Trying to get nomenclature characteristic({s_itemProp})")
                c_charRef = self.c_v8.Catalogs.ХарактеристикиНоменклатуры.EmptyRef()
                if s_itemProp:
                    c_charRef = self.c_v8.Catalogs.ХарактеристикиНоменклатуры.FindByDescription(
                        s_itemProp,
                        True,
                        c_nomRef
                    )
                log_sys("Characteristic successfully fetched")
                
                # Fetch price
                log_sys("Trying to get nomenclature price...")
                try:
                    # Determine price type to use from order object
                    s_price_type_name = getattr(c_orderObjIn, "s_price_type", "")
                    if not s_price_type_name:
                        s_price_type_name = "Розничная"

                    def get_variety_price(variety):
                        # Try to match by s_type of the Price object
                        for price_attr in ["c_priceRetail", "c_priceOpt", "c_pricePurchase"]:
                            price_obj = getattr(variety, price_attr, None)
                            if price_obj and price_obj.s_type == s_price_type_name:
                                return price_obj.n_value
                        # Fallback mappings based on standard names
                        if s_price_type_name == "Оптовая":
                            return variety.c_priceOpt.n_value
                        elif s_price_type_name == "Закупочная":
                            return variety.c_pricePurchase.n_value
                        else:
                            return variety.c_priceRetail.n_value

                    # 1. Price from variety passed in c_item
                    n_passedPrice = 0.0
                    has_variety = getattr(c_item, "c_variety", None) is not None
                    if has_variety:
                        n_passedPrice = get_variety_price(c_item.c_variety)

                    # 2. Get the actual price from 1C
                    n_1cPrice = 0.0
                    try:
                        c_tempNom = self.c_connection.nomenclature.get(s_codeIn=c_item.s_productCode)
                        if c_tempNom and c_tempNom.l_variety:
                            c_foundVariety = None
                            for c_variety in c_tempNom.l_variety:
                                if not s_itemProp:
                                    c_foundVariety = c_variety
                                    break
                                
                                for c_char in c_variety.l_characteristics:
                                    if c_char.s_value == s_itemProp or f"{c_char.s_name}: {c_char.s_value}" == s_itemProp:
                                        c_foundVariety = c_variety
                                        break
                                if c_foundVariety:
                                    break
                            
                            if not c_foundVariety:
                                c_foundVariety = c_tempNom.l_variety[0]
                                
                            n_1cPrice = get_variety_price(c_foundVariety)
                    except Exception as e:
                        log_sys(f"Failed to fetch actual 1C price for comparison: {e}", 1)

                    # 3. Compare and set final actual price
                    if has_variety:
                        if n_1cPrice > 0.0:
                            log_sys(f"Comparing variety price ({n_passedPrice}) with 1C price ({n_1cPrice}) for {c_item.s_productCode}")
                            if abs(n_passedPrice - n_1cPrice) > 0.01:
                                log_sys(f"Price mismatch detected for {c_item.s_productCode}: variety price is {n_passedPrice}, but 1C price is {n_1cPrice}. Using 1C price.", 1)
                            n_actualPrice = n_1cPrice
                        else:
                            log_sys(f"Could not fetch 1C price for {c_item.s_productCode} or price is 0. Using variety price ({n_passedPrice}).")
                            n_actualPrice = n_passedPrice
                    else:
                        n_actualPrice = n_1cPrice
                except Exception as e:
                    log_sys(f"Cannot get nomenclature price: {e}. Setting price to 0", 1)
                    n_actualPrice = 0.0

                log_sys("Creating new orderItem table row. Trying to add new nomenclature...")
                try:
                    c_row = c_newOrder.Товары.Add()
                    c_row.ЕдиницаИзмерения = c_nomRef.ЕдиницаХраненияОстатков
                    c_row.Номенклатура = c_nomRef
                    c_row.ХарактеристикаНоменклатуры = c_charRef
                    c_row.Количество = int(c_item.n_productCount)
                    c_row.Коэффициент = 1
                    c_row.Цена = float(n_actualPrice)
                    c_row.Сумма = float(c_row.Количество * c_row.Цена)
                    log_sys("Nomenclature was successfully added")
                except Exception as e:
                    log_sys(f"Failed adding nomenclature: {e}", 1)
                
            # Add customer info and metadata directly to order comment before writing
            s_comment_parts = []
            if b_isBotCounteragent and c_customer:
                s_pib = f"{c_customer.s_customerSurname} {c_customer.s_customerName} {c_customer.s_customerPatronymic}".strip()
                if s_pib:
                    s_comment_parts.append(s_pib)
                if c_customer.s_customerPhone:
                    s_comment_parts.append(c_customer.s_customerPhone)
                if c_customer.s_customerId:
                    s_comment_parts.append(c_customer.s_customerId)
            
            s_ttn = getattr(c_orderObjIn, "s_TTN", "")
            s_status = getattr(c_orderObjIn, "s_status", "")
            if s_ttn:
                s_comment_parts.append(s_ttn)
            if s_status:
                s_comment_parts.append(s_status)
                
            if s_comment_parts:
                c_newOrder.Комментарий = " ".join(s_comment_parts)

            try:
                log_sys("Everything done. Trying to post order...")
                c_newOrder.Write(self.c_v8.DocumentWriteMode.Posting)
                log_sys(f"Order was successfully posted. Code: {c_newOrder.Номер}")
                c_orderObjIn.n_orderCode = c_newOrder.Номер
                return c_newOrder.Номер
            except Exception as e:
                try:
                    log_sys(f"Failed posting order ({e}). Trying to save it...")
                    c_newOrder.Write(self.c_v8.DocumentWriteMode.Write)
                    log_sys(f"Order was successfully saved. Returning code: {c_newOrder.Номер}")
                    c_orderObjIn.n_orderCode = c_newOrder.Номер
                    return c_newOrder.Номер
                except Exception as e2:
                    log_sys(f"Failed saving order: {e2}")
                    return ""

        except Exception as e:
            log_sys(f"Unexpected error in posting order: {e}. Returning \"\"", 1)
            return ""

    def get(self, s_codeIn: str):
        """Retrieves and parses a customer order by its 1C document number."""
        if not self.c_v8:
            log_sys("Failed to get order: No connection to 1C. Returning None", 1)
            return None

        if len(s_codeIn) < 2:
            log_sys(f"Failed to get order: Wrong code format ({s_codeIn}). Returning None", 1)
            return None

        try:
            log_sys(f"Searching for order with number: {s_codeIn}...")
            c_orderRef = self.c_v8.Documents.ЗаказПокупателя.FindByNumber(
                s_codeIn, 
                datetime.now(self.c_connection.tz_kiev).replace(tzinfo=None)
            )

            if c_orderRef.IsEmpty():
                log_sys(f"Order with number {s_codeIn} not found in 1C.", 1)
                return None

            log_sys("Order found. Extracting data...")
            c_orderObj1c = c_orderRef.GetObject()

            s_comment = ""
            try:
                s_comment = self.c_v8.String(c_orderObj1c.Комментарий)
            except Exception as e:
                log_sys(f"Failed to get comment from 1C order document: {e}", 1)

            s_telegramId = s_comment
            c_customer = structures.Customer(s_customerIdIn=s_telegramId)
            log_sys(f"Customer ID extracted from comments: {s_telegramId}")

            s_price_type = ""
            try:
                if not c_orderObj1c.ТипЦен.IsEmpty():
                    s_price_type = c_orderObj1c.ТипЦен.Наименование
            except Exception as e:
                log_sys(f"Failed to get price type from 1C order document: {e}", 1)

            l_orderItemsList = []
            for c_row in c_orderObj1c.Товары:
                s_article = c_row.Номенклатура.Код
                c_variety = None
                c_charRef = c_row.ХарактеристикаНоменклатуры
                if not c_charRef.IsEmpty():
                    s_charName = c_charRef.Наименование
                    l_chars = self.c_connection.characteristics.get(c_charRef, s_charName)
                    c_variety = structures.Variety(
                        c_priceRetailIn=structures.Price(c_row.Цена, s_type="Розничная"),
                        c_priceOptIn=structures.Price(0.0, s_type="Оптовая"),
                        d_countIn={},
                        l_characteristicsIn=l_chars
                    )

                c_item = structures.OrderItem(
                    s_productCodeIn=s_article,
                    c_varietyIn=c_variety,
                    n_productCountIn=c_row.Количество
                )
                l_orderItemsList.append(c_item)

            c_resultOrder = structures.Order(
                c_orderCustomerIn=c_customer,
                l_orderItemsListIn=l_orderItemsList,
                n_orderCodeIn=s_codeIn,
                s_price_typeIn=s_price_type,
                s_commentIn=s_comment
            )

            log_sys(f"Order {s_codeIn} successfully fetched and parsed.")
            return c_resultOrder

        except Exception as e:
            log_sys(f"Error occurred while retrieving order {s_codeIn}: {e}", 1)
            return None

    def get_today(self) -> list:
        """Retrieves all orders created today for the configured counteragent bot."""
        if not self.c_v8:
            log_sys("Failed to get today's orders: No connection to 1C.", 1)
            return []

        if len(self.c_connection.s_counteragent_code) < 1:
            log_sys("Failed to get today's orders: No counteragent code. Returning []", 1)
            return []
            
        try:
            log_sys("Fetching today's orders for bot counteragent...")
            c_clientRef = self.c_v8.Catalogs.Контрагенты.FindByCode(self.c_connection.s_counteragent_code)

            if c_clientRef is None or c_clientRef.IsEmpty():
                log_sys(f"Counteragent with code {self.c_connection.s_counteragent_code} not found in 1C.", 1)
                return []

            c_startOfToday = datetime.now(self.c_connection.tz_kiev).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=None
            )
            c_query = self.c_v8.NewObject("Query")
            c_query.Text = """
                SELECT Номер AS Number
                FROM Документ.ЗаказПокупателя
                WHERE Дата >= &StartDate
                  AND Контрагент = &ClientBot
                  AND ПометкаУдаления = FALSE
                ORDER BY Дата DESC
            """
            c_query.SetParameter("StartDate", c_startOfToday)
            c_query.SetParameter("ClientBot", c_clientRef)

            c_result = c_query.Execute()
            l_ordersList = []

            if not c_result.IsEmpty():
                c_selection = c_result.Select()
                log_sys("Found some orders. Starting to parse...")

                while c_selection.Next():
                    c_orderObj = self.get(c_selection.Number)
                    if c_orderObj:
                        l_ordersList.append(c_orderObj)

            log_sys(f"Successfully retrieved {len(l_ordersList)} orders for today.")
            return l_ordersList

        except Exception as e:
            log_sys(f"Error in getTodayOrders: {e}", 1)
            return []

    def update_info(self, c_orderObjIn) -> bool:
        """Updates the comment details of an order in 1C with PIB, phone, customer ID, TTN and status."""
        if not self.c_v8:
            log_sys("Failed to update order info: No connection to 1C.", 1)
            return False

        try:
            c_orderRef = self.c_v8.Documents.ЗаказПокупателя.FindByNumber(c_orderObjIn.n_orderCode)

            if c_orderRef.IsEmpty():
                log_sys(f"Order with number {c_orderObjIn.n_orderCode} not found for update.", 1)
                return False

            c_orderObj1c = c_orderRef.GetObject()
            c_customer = c_orderObjIn.c_orderCustomer

            s_pib = f"{c_customer.s_customerSurname} {c_customer.s_customerName} {c_customer.s_customerPatronymic}".strip()
            s_phone = c_customer.s_customerPhone
            s_customerId = c_customer.s_customerId
            s_ttn = c_orderObjIn.s_TTN
            s_status = c_orderObjIn.s_status

            s_newComment = f"{s_pib} {s_phone} {s_customerId} {s_ttn} {s_status}"
            c_orderObj1c.Комментарий = s_newComment
            c_orderObj1c.Write(self.c_v8.DocumentWriteMode.Write)

            log_sys(f"Order {c_orderObjIn.n_orderCode} info successfully updated in 1C.")
            return True

        except Exception as e:
            log_sys(f"Error occurred while updating order {c_orderObjIn.n_orderCode}: {e}", 1)
            return False
